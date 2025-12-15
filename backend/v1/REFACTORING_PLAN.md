# Backend Codebase Restructuring Plan (MVP-Pragmatic Version)

## Executive Summary

This plan outlines a pragmatic refactor of the Bot Builder backend to eliminate critical issues and establish clean, maintainable code without over-engineering the file structure.

**Approach**: Focused refactor with practical file organization
**Priority**: Clean code, eliminate duplication, fix critical bugs
**Duration**: 2-3 weeks full-time
**Risk**: Medium (targeted improvements with breaking changes where needed)

---

## Critical Issues Identified

### Severity: CRITICAL
1. **God Objects**: ConversationEngine (533 lines), SessionManager (600+ lines)
2. **Code Duplication**: ~400 lines duplicated (path resolution, retry logic, validation)
3. **Missing Foreign Key**: Session.flow_id has no FK constraint (data integrity risk)
4. **Tight Coupling**: Processors hardcoded in engine, no dependency injection
5. **Transaction Chaos**: Auto-commit in get_db() + explicit commits = double commit risk
6. **No Repository Pattern**: Database queries scattered everywhere

### Severity: HIGH
7. **Inconsistent Error Handling**: Mix of exceptions, booleans, and error objects
8. **N+1 Query Issues**: No SQLAlchemy relationships, manual querying everywhere
9. **Redis Error Recovery**: Inconsistent fallback, no circuit breaker, silent failures
10. **Flat Exception Hierarchy**: 19 exceptions at same level, no categorization
11. **String-Based Parsing**: Condition evaluator uses regex hacks instead of proper parser

---

## Improved Architecture: Pragmatic & Consolidated

**Philosophy**: Keep existing structure where it makes sense, consolidate improvements into fewer files.

### New File Structure

```
backend/v1/app/
├── api/                   # API endpoints (keep existing)
│   ├── auth.py           # ✅ Keep as-is (minor cleanup)
│   ├── bots.py           # 🔧 Refactor: remove duplicate ownership checks
│   ├── flows.py          # 🔧 Refactor: standardize error handling
│   ├── webhooks.py       # ✅ Keep as-is (minor cleanup)
│   └── middleware.py     # ✨ NEW: consolidated middleware
│
├── core/                  # Business logic
│   ├── engine.py         # 🔧 REFACTOR: 3 classes in ONE file
│   │                     #    - KeywordMatcher, FlowExecutor, Orchestrator
│   ├── session_manager.py # 🔧 Refactor: remove duplication
│   ├── template_engine.py # ✅ Keep as-is
│   ├── validators.py     # 🔧 CONSOLIDATE 3 files into 1
│   ├── conditions.py     # 🔧 CONSOLIDATE 2 files into 1
│   └── redis_manager.py  # 🔧 Add circuit breaker inline
│
├── processors/           # Node processors
│   ├── base_processor.py # ✅ Keep as-is
│   ├── factory.py        # ✨ NEW: processor factory
│   ├── retry_handler.py  # ✨ NEW: extracted retry logic
│   ├── prompt_processor.py   # 🔧 Use retry_handler
│   ├── menu_processor.py     # 🔧 Use retry_handler
│   └── [other processors]    # ✅ Keep as-is
│
├── repositories/         # ✨ NEW: Data access layer
│   ├── base.py
│   ├── bot_repository.py
│   ├── flow_repository.py
│   ├── session_repository.py
│   └── user_repository.py
│
├── models/               # ORM models
│   ├── user.py          # 🔧 Add relationships
│   ├── bot.py           # 🔧 Add relationships
│   ├── flow.py          # 🔧 Add FK constraint + relationships
│   ├── session.py       # 🔧 Add FK constraint + relationships
│   └── node_configs.py  # ✅ Keep as-is (excellent)
│
├── utils/                # Utilities
│   ├── shared.py        # ✨ NEW: PathResolver, TypeConverter, ExpressionParser
│   ├── constants.py     # 🔧 Better organization
│   ├── exceptions.py    # 🔧 Proper hierarchy
│   ├── logger.py        # 🔧 Minor improvements
│   └── security.py      # ✅ Keep as-is
│
├── config.py            # 🔧 Nested configs, better validation
├── database.py          # 🔧 Remove auto-commit
├── dependencies.py      # 🔧 Reusable ownership checking
└── main.py              # 🔧 Minor cleanup
```

**Result**:
- **New Files**: 11 (shared.py, repositories×5, middleware.py, factory.py, retry_handler.py, validators.py, conditions.py, engine.py)
- **Modified Files**: ~20
- **Deleted Files**: 6 (consolidated into new files)
- **Net Change**: +5 files (pragmatic for MVP)

---

## Phase 1: Shared Utilities - Eliminate Duplication (Days 1-2)

### 1.1 Create Consolidated Utilities

**File**: `app/utils/shared.py` (NEW - ~300 lines)

Consolidates all shared abstractions that are currently duplicated:

```python
"""
Shared utilities used across the codebase
Eliminates ~400 lines of code duplication
"""

class PathResolver:
    """
    Centralized dot-notation path resolution
    REPLACES duplicate code in:
    - template_engine.py lines 127-186
    - condition_evaluator.py lines 163-210
    - validation_system.py lines 232-258
    """
    @staticmethod
    def resolve(path: str, context: Dict[str, Any]) -> Optional[Any]:
        """Resolve 'context.user.name' with null-safety"""

class TypeConverter:
    """
    Centralized type conversion
    REPLACES duplicate logic in:
    - validation_system.py lines 329-416
    - prompt_processor.py and menu_processor.py
    """
    @staticmethod
    def to_string(value: Any) -> str: ...
    @staticmethod
    def to_integer(value: Any) -> Optional[int]: ...
    @staticmethod
    def to_boolean(value: Any) -> Optional[bool]: ...
    @staticmethod
    def to_array(value: Any) -> Optional[List]: ...

class ExpressionParser:
    """
    Proper AST-based expression parser
    REPLACES string hacks in:
    - condition_evaluator.py (string splitting)
    - validation_system.py (string replacement)
    """
    def parse(self, expression: str) -> ExpressionNode: ...
    def evaluate(self, expression: str, context: Dict) -> Any: ...
```

### 1.2 Refactor Exception Hierarchy

**File**: `app/utils/exceptions.py` (REFACTOR existing)

Add proper categorization and structured metadata:

```python
class BotBuilderException(Exception):
    """Base exception with structured metadata"""
    def __init__(self, message: str, error_code: str = None, **metadata):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.metadata = metadata

# Category 1: System/Infrastructure
class SystemException(BotBuilderException): ...
class DatabaseError(SystemException): ...
class CacheError(SystemException): ...

# Category 2: Validation
class ValidationException(BotBuilderException): ...
class FlowValidationError(ValidationException): ...

# Category 3: Session Management
class SessionException(BotBuilderException): ...
class SessionExpiredError(SessionException): ...

# Category 4: Execution
class ExecutionException(BotBuilderException): ...
class NoMatchingRouteError(ExecutionException): ...
```

### 1.3 Improve Configuration

**File**: `app/config.py` (REFACTOR existing)

Add nested configuration groups:

```python
class DatabaseConfig(BaseSettings):
    url: str
    pool_size: int = 5
    max_overflow: int = 10

class RedisConfig(BaseSettings):
    url: str
    enabled: bool = True
    socket_timeout: int = 5

class Settings(BaseSettings):
    # Nested configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()

    # Cross-field validation
    @model_validator(mode='after')
    def validate_dependencies(self):
        if self.redis.enabled and not self.redis.url:
            raise ValueError("REDIS_URL required")
```

---

## Phase 2: Data Layer - Critical Fixes (Days 3-5)

### 2.1 Add Missing Foreign Key Constraint (CRITICAL!)

**File**: `app/models/session.py` (MODIFY)

```python
class Session(Base):
    flow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("flows.id", ondelete="CASCADE"),  # ← ADD THIS
        nullable=False,
        index=True
    )
```

**Migration**: Create Alembic migration to add FK constraint.

### 2.2 Add SQLAlchemy Relationships

Solve N+1 query problems by adding proper relationships:

**File**: `app/models/bot.py`
```python
flows = relationship("Flow", back_populates="bot", lazy="selectinload")
sessions = relationship("Session", back_populates="bot", lazy="noload")
```

**File**: `app/models/flow.py`
```python
bot = relationship("Bot", back_populates="flows")
sessions = relationship("Session", back_populates="flow")
```

**File**: `app/models/session.py`
```python
bot = relationship("Bot", back_populates="sessions")
flow = relationship("Flow", back_populates="sessions")
```

### 2.3 Create Repository Pattern

**NEW Directory**: `app/repositories/`

**File**: `app/repositories/base.py` (~50 lines)
```python
class BaseRepository(Generic[T]):
    """Base repository with shared methods"""

    def __init__(self, session: AsyncSession, model_class):
        self.session = session
        self.model = model_class

    async def get_by_id(self, id: UUID) -> Optional[T]: ...
    async def add(self, entity: T) -> T: ...
    async def delete(self, entity: T): ...
```

**File**: `app/repositories/bot_repository.py` (~50 lines)
```python
class BotRepository(BaseRepository[Bot]):
    async def get_user_bots(self, user_id: UUID) -> List[Bot]:
        """Get user's bots with eager-loaded flows (solves N+1)"""
        stmt = (
            select(Bot)
            .where(Bot.owner_user_id == user_id)
            .options(selectinload(Bot.flows))  # ← Eager load!
        )
        return await self.session.execute(stmt).scalars().all()
```

Similar repositories for: `flow_repository.py`, `session_repository.py`, `user_repository.py`

### 2.4 Fix Transaction Management

**File**: `app/database.py` (MODIFY)

Remove auto-commit - services must commit explicitly:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    CRITICAL FIX: NO AUTO-COMMIT
    Services now control transactions explicitly
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # REMOVED: await session.commit()
```

---

## Phase 3: Core Engine & Services Refactor (Days 6-10)

### 3.1 Refactor Services to Use Repositories

**File**: `app/services/bot_service.py` (REFACTOR)

```python
class BotService:
    """Bot business logic using repositories"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bot_repo = BotRepository(db)

    async def create_bot(self, owner_user_id: UUID, name: str, description: Optional[str]) -> Bot:
        """Create bot with EXPLICIT transaction"""
        bot = Bot(owner_user_id=owner_user_id, name=name, description=description)
        bot = await self.bot_repo.add(bot)
        await self.db.commit()  # ← EXPLICIT
        await self.db.refresh(bot)
        return bot

    async def get_user_bots(self, user_id: UUID) -> List[Bot]:
        """Uses repository with eager loading - no N+1"""
        return await self.bot_repo.get_user_bots(user_id)
```

**Changes**:
- Use repositories instead of direct SQL
- Explicit commits (no auto-commit)
- No cache logic in service (separate concern)
- ~150 lines (down from 262)

### 3.2 Break Up ConversationEngine

**File**: `app/core/engine.py` (NEW - replaces conversation_engine.py)

**Strategy**: Keep in ONE file but separate into 3 focused classes

```python
"""
Conversation Engine - Refactored
Total ~360 lines (down from 533) in ONE file with 3 focused classes
"""

# ===== Class 1: KeywordMatcher (~80 lines) =====
class KeywordMatcher:
    """Matches trigger keywords to flows"""

    async def find_matching_flow(
        self,
        bot_id: UUID,
        message: str,
        db: AsyncSession
    ) -> Optional[Flow]:
        # Cache lookup → Database fallback → Wildcard handling

# ===== Class 2: FlowExecutor (~200 lines) =====
class FlowExecutor:
    """Executes flow nodes with auto-progression"""

    async def execute_flow(
        self,
        session: Session,
        user_input: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        # Auto-progression loop → Processor dispatch → Route evaluation

# ===== Class 3: ConversationOrchestrator (~80 lines) =====
class ConversationOrchestrator:
    """Main orchestration - simple and focused"""

    async def process_message(
        self,
        bot_id: UUID,
        channel: str,
        channel_user_id: str,
        message_text: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        # 1. Get/create session
        # 2. Match flow (if new)
        # 3. Execute flow
```

**Why one file?**
- Classes work together closely
- ~360 lines is manageable
- Easier to navigate than 3 separate files
- Still achieves separation of concerns

### 3.3 Consolidate Validation & Conditions

**File**: `app/core/validators.py` (NEW - consolidates 3 files)

```python
"""
Consolidates: validation_system.py + flow_validator.py + route_validator.py
~500 lines (down from ~1500)
"""

from app.utils.shared import PathResolver, TypeConverter, ExpressionParser

class ValidationEngine:
    """Input validation using shared utilities"""

class FlowValidator:
    """Flow structure validation"""

class RouteValidator:
    """Route validation"""
```

**File**: `app/core/conditions.py` (NEW - consolidates 2 files)

```python
"""
Consolidates: condition_evaluator.py + route_sorter.py
~250 lines (down from ~400)
"""

from app.utils.shared import PathResolver, ExpressionParser

class ConditionEvaluator:
    """Evaluates route conditions - uses ExpressionParser (no more string hacks!)"""

class RouteSorter:
    """Sorts routes by priority"""
```

### 3.4 Add Processor Factory & Retry Handler

**File**: `app/processors/factory.py` (NEW - ~50 lines)

```python
class ProcessorFactory:
    """Factory for creating node processors - eliminates hardcoding"""

    def __init__(self, template_engine, validator, evaluator, http_client):
        self._processors = {}
        self._dependencies = {...}

        # Register processors
        self.register(NodeType.PROMPT, PromptProcessor)
        self.register(NodeType.MENU, MenuProcessor)
        # ... extensible!

    def create(self, node_type: str) -> BaseProcessor:
        return self._processors[node_type](**self._dependencies)
```

**File**: `app/processors/retry_handler.py` (NEW - ~80 lines)

```python
class RetryHandler:
    """
    Centralized retry logic
    ELIMINATES duplication in prompt_processor.py and menu_processor.py
    """

    async def handle_validation_failure(
        self,
        session: Session,
        error_message: str,
        fail_route: Optional[str]
    ) -> RetryResult:
        # Unified retry handling with attempt counting
```

---

## Phase 4: API & Infrastructure (Days 11-15)

### 4.1 Add API Middleware

**File**: `app/api/middleware.py` (NEW - ~150 lines)

```python
"""Consolidated middleware for API layer"""

class OwnershipChecker:
    """
    Reusable ownership verification
    ELIMINATES 5x duplication across flows.py and bots.py
    """

# Global exception handlers
@app.exception_handler(ValidationException)
async def handle_validation_error(...):
    return JSONResponse(status_code=400, ...)

@app.exception_handler(SessionException)
async def handle_session_error(...):
    return JSONResponse(status_code=410 if expired else 404, ...)
```

**Update all API endpoints to**:
- Use OwnershipChecker (remove duplicate code)
- Use repositories via services
- Return proper HTTP status codes (no more 201 for validation errors!)

### 4.2 Add Circuit Breaker to Redis

**File**: `app/core/redis_manager.py` (REFACTOR existing)

Add circuit breaker pattern inline (~100 extra lines):

```python
class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class RedisManager:
    def __init__(self, ...):
        self.circuit_state = CircuitState.CLOSED
        self.failure_count = 0

    async def _execute_with_circuit_breaker(self, func, *args):
        """Wrap operations with circuit breaker"""
        if self.circuit_state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.circuit_state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit is OPEN - degraded mode")
        # ... circuit breaker logic
```

**Why inline?**
- Adds ~100 lines to existing 524-line file → total ~600 lines (manageable)
- Avoids creating separate circuit_breaker.py file
- Simpler than full separate abstraction for MVP

---

## Phase 5: Final Touches (Days 16-18)

### 5.1 Update Remaining Files

Minor refactors (keep existing structure):
- `app/dependencies.py`: Use OwnershipChecker, split get_current_user
- `app/main.py`: Update imports, minor cleanup
- `app/schemas/*.py`: Consolidate duplicate validation

### 5.2 Delete Old Files

After consolidation complete, delete:

```
app/core/conversation_engine.py  → app/core/engine.py
app/core/validation_system.py    → app/core/validators.py
app/core/flow_validator.py       → app/core/validators.py
app/core/route_validator.py      → app/core/validators.py
app/core/condition_evaluator.py  → app/core/conditions.py
app/core/route_sorter.py         → app/core/conditions.py
```

---

## Migration Timeline

### Week 1: Foundation
- **Days 1-2**: Shared utilities, exceptions, config
- **Days 3-5**: FK constraints, relationships, repositories, database.py

### Week 2: Core Refactor
- **Days 6-10**: Services, engine breakup, validation consolidation, processors

### Week 3: Polish
- **Days 11-15**: API middleware, Redis circuit breaker
- **Days 16-18**: Minor refactors, delete old files, manual testing

---

## Success Metrics

### Files Changed
- **New Files**: 11
- **Modified Files**: ~20
- **Deleted Files**: 6
- **Net Change**: +5 files (minimal growth)

### Code Quality Improvements
- **Code duplication**: 90% reduction (~400 → ~40 lines)
- **Avg method length**: <20 lines (from 45)
- **ConversationEngine**: 533 → 360 lines, 1 class → 3 focused classes
- **Cyclomatic complexity**: <8 (from 12-15)
- **God objects**: Eliminated

### Critical Fixes Delivered
✅ FK constraint added (data integrity)
✅ SQLAlchemy relationships (N+1 queries solved)
✅ Transaction management fixed (no auto-commit)
✅ Code duplication eliminated via shared utilities
✅ Exception hierarchy improved with categories
✅ Redis circuit breaker added for resilience
✅ Repository pattern centralizes data access
✅ Processor factory eliminates tight coupling

---

## Risks & Mitigation

### High Risk Items
1. **Database Migration**: FK constraint may take time on large tables
   - **Mitigation**: Run during low-traffic window, test on staging first

2. **Breaking Changes**: API responses may change
   - **Mitigation**: Acceptable per requirements (breaking changes allowed)

### Medium Risk Items
3. **Complete Rewrite**: High chance of introducing bugs
   - **Mitigation**: Extensive manual testing, keep old code on branch

4. **Performance Changes**: New architecture may perform differently
   - **Mitigation**: Performance testing before deploy, add metrics

---

## Conclusion

This pragmatic refactor achieves:

✅ **Clean Code**: Eliminates god objects, removes duplication, follows SOLID principles
✅ **Maintainability**: Clear structure, focused classes, easy to navigate
✅ **Critical Fixes**: FK constraints, N+1 queries, transactions, error handling
✅ **Minimal Complexity**: Net +5 files, consolidates instead of proliferates
✅ **MVP-Ready**: No over-engineering, practical improvements only

**Duration**: 2-3 weeks
**Risk**: Medium (targeted changes, breaking changes allowed)
**Outcome**: Production-ready, maintainable codebase that's a pleasure to work with
