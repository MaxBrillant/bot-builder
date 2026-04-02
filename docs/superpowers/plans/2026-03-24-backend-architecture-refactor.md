# Backend Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split two oversized backend files into focused modules without changing any logic or breaking any existing imports.

**Architecture:** Pure file reorganization — extract natural class boundaries that already exist in the code. Backward-compat shims preserve all existing import sites. Two independent tasks, each producing a clean commit.

**Tech Stack:** Python 3.11, FastAPI, pytest

---

### Task 1: Split validators.py into input_validator and flow_validator

**Files:**
- Create: `backend/v1/app/core/input_validator.py`
- Create: `backend/v1/app/core/flow_validator.py`
- Modify: `backend/v1/app/core/validators.py` (replace with thin re-export shim)

**Known import sites (all remain unchanged — served by shim):**
- `app/services/flow_service.py` → `FlowValidator`
- `app/processors/base_processor.py` → `InputValidator as ValidationSystem`
- `app/processors/factory.py` → `InputValidator as ValidationSystem`
- `app/core/engine.py` → `InputValidator as ValidationSystem`
- `app/core/__init__.py` → `InputValidator as ValidationSystem, FlowValidator`

- [ ] **Step 1: Run existing tests to establish baseline**

```bash
cd backend/v1
source venv/bin/activate
pytest --tb=short -q
```
Expected: all tests pass. Note the count. If any fail, stop — do not proceed with a failing baseline.

- [ ] **Step 2: Verify ValidationSystem alias only maps to InputValidator**

```bash
grep -rn "ValidationSystem" backend/v1/app/ --include="*.py"
```
Expected: all hits use `ValidationSystem` as `InputValidator` (prompt/input validation only). If any hit expects `FlowValidator` or `RouteConditionValidator` behavior, stop and reassess the shim.

- [ ] **Step 3: Create `backend/v1/app/core/input_validator.py`**

Create the file with this exact content — module docstring, imports, then the `InputValidator` class copied verbatim from `validators.py`. The class starts at the `class InputValidator:` line and ends just before `# ===== Class 2: RouteConditionValidator`. Copy every line of it, including all private methods. Do not change any logic.

```python
"""
Input Validator
Validates user input in PROMPT nodes (REGEX, EXPRESSION validation types).
"""
import re
from typing import Any, Dict
from app.utils.shared import PathResolver, TypeConverter
from app.utils.logger import get_logger
from app.utils.exceptions import InputValidationError
from app.utils.constants import VariableType, SystemConstraints, RegexPatterns

logger = get_logger(__name__)

# Paste InputValidator class here verbatim (everything from "class InputValidator:" through
# the end of the convert_type method, ending before "# ===== Class 2")
```

- [ ] **Step 4: Create `backend/v1/app/core/flow_validator.py`**

Create the file with this exact content — module docstring, imports, then the three classes copied verbatim from `validators.py`. Copy starting from `# ===== Class 2: RouteConditionValidator` through the end of the file (the `ValidationSystem = InputValidator` alias line is NOT included — that stays in the shim). Do not change any logic.

```python
"""
Flow Validator
Validates flow structure on submission.
Contains: RouteConditionValidator, ValidationResult, FlowValidator
"""
import re
from typing import Any, Dict, Optional, List, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError
from app.utils.shared import PathResolver, TypeConverter
from app.utils.logger import get_logger
from app.utils.exceptions import InputValidationError
from app.utils.constants import (
    NodeType, VariableType, ValidationType, MenuSourceType,
    SystemConstraints, ReservedKeywords, RegexPatterns
)
from app.utils.security import validate_node_id_format
from app.models.node_configs import FlowNode

logger = get_logger(__name__)

# Paste RouteConditionValidator, ValidationResult, and FlowValidator classes here verbatim
# (everything from "class RouteConditionValidator:" to the end of FlowValidator,
#  stopping before "# ===== Backward Compatibility Aliases =====")
```

- [ ] **Step 5: Replace `backend/v1/app/core/validators.py` with thin re-export shim**

Replace the entire file content with:

```python
"""
Validators — backward-compatibility re-export shim.
For new code, import directly from input_validator or flow_validator.
"""
from app.core.input_validator import InputValidator
from app.core.flow_validator import FlowValidator, RouteConditionValidator, ValidationResult

# Alias used by engine.py, base_processor.py, factory.py
ValidationSystem = InputValidator

__all__ = [
    'InputValidator',
    'FlowValidator',
    'RouteConditionValidator',
    'ValidationResult',
    'ValidationSystem',
]
```

- [ ] **Step 6: Run tests to verify no regressions**

```bash
pytest --tb=short -q
```
Expected: same count of passing tests as Step 1. Zero failures. If any fail, do not commit — debug the import path.

- [ ] **Step 7: Commit**

```bash
git add backend/v1/app/core/input_validator.py \
        backend/v1/app/core/flow_validator.py \
        backend/v1/app/core/validators.py
git commit -m "refactor: split validators.py into input_validator and flow_validator"
```

---

### Task 2: Extract DistributedCircuitBreaker from redis_manager

**Files:**
- Create: `backend/v1/app/core/circuit_breaker.py`
- Modify: `backend/v1/app/core/redis_manager.py`

No external import sites use `DistributedCircuitBreaker`, `CircuitBreaker`, or `CircuitState` — confirmed by grep (all external callers only import `redis_manager` and `get_redis_manager`). No shim needed.

- [ ] **Step 1: Verify no external imports of circuit breaker classes**

```bash
grep -rn "DistributedCircuitBreaker\|CircuitBreaker\|CircuitState" \
  backend/v1/app/ --include="*.py" | grep -v "redis_manager.py"
```
Expected: no output. If any hits exist, update the approach (add re-exports to `redis_manager.py`) before proceeding.

- [ ] **Step 2: Create `backend/v1/app/core/circuit_breaker.py`**

Create the file with this exact content — module docstring, imports, then the classes copied verbatim from `redis_manager.py`. Copy the `CircuitState` enum, the `DistributedCircuitBreaker` class, and the `CircuitBreaker` alias. These are the only things that belong in this file. Do not change any logic.

```python
"""
Distributed Circuit Breaker
Prevents cascading Redis failures. State stored in Redis so all API instances share it.
Accepts a redis client via set_redis() — no dependency on RedisManager or app config.
"""
import asyncio
from typing import Optional
from datetime import datetime
from enum import Enum
import redis.asyncio as redis
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Paste CircuitState enum, DistributedCircuitBreaker class, and CircuitBreaker alias
# here verbatim from redis_manager.py (everything from "class CircuitState(Enum):"
# through "CircuitBreaker = DistributedCircuitBreaker", stopping before "class RedisManager:")
```

- [ ] **Step 3: Update `backend/v1/app/core/redis_manager.py`**

Two changes only — do not touch anything else:

1. Add this import near the top of the file (after existing imports):
```python
from app.core.circuit_breaker import CircuitState, DistributedCircuitBreaker, CircuitBreaker
```

2. Delete the now-duplicated symbols from `redis_manager.py`: the `CircuitState` enum, the entire `DistributedCircuitBreaker` class, and the `CircuitBreaker = DistributedCircuitBreaker` alias line. Identify them by name — do not rely on line numbers. Everything from `class CircuitState(Enum):` through `CircuitBreaker = DistributedCircuitBreaker` (inclusive) should be removed.

- [ ] **Step 4: Run tests to verify no regressions**

```bash
pytest --tb=short -q
```
Expected: same count of passing tests as Task 1 Step 6. Zero failures.

- [ ] **Step 5: Commit**

```bash
git add backend/v1/app/core/circuit_breaker.py \
        backend/v1/app/core/redis_manager.py
git commit -m "refactor: extract circuit_breaker from redis_manager"
```
