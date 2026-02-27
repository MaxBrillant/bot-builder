# Bot Builder Test Suite

Comprehensive test coverage for BOT_BUILDER_SPECIFICATIONS.md (3,690 lines) - organized for optimal TDD workflow.

## Overview

- **Total Tests**: 524 tests
- **Organization**: By implementation module and test type
- **Test IDs**: 001-524 (preserved in docstrings for traceability)

## Directory Structure

```
tests/
├── unit/              295 tests - Fast < 1s per test
│   ├── validators/     96 tests - Flow, input, constraint validation
│   ├── processors/     79 tests - All 6 node type processors
│   ├── core/           88 tests - Engine components
│   └── utils/          32 tests - Type conversion, trigger matching
│
├── integration/        37 tests - Medium 1-5s per test
│   ├── test_flow_execution.py
│   ├── test_route_evaluation.py
│   ├── test_array_truncation.py
│   └── test_retry_logic.py
│
├── e2e/                30 tests - Slow 5-30s per test
│   ├── test_forms.py
│   ├── test_surveys.py
│   ├── test_bookings.py
│   ├── test_ecommerce.py
│   ├── test_support.py
│   ├── test_onboarding.py
│   └── test_conversation_patterns.py
│
├── security/           50 tests - Security focused
│   ├── test_security_core.py
│   └── test_security_depth.py
│
└── system/            112 tests - System level
    ├── test_negative_capabilities.py
    ├── test_error_messages.py
    ├── test_bot_management.py
    ├── test_best_practices.py
    └── test_core_capabilities.py
```

## Quick Start

```bash
# Run all tests
pytest

# Run by speed (TDD workflow)
pytest unit/           # Fast - run frequently during development
pytest integration/    # Medium - run before committing
pytest e2e/            # Slow - run before PR

# Run by component
pytest unit/processors/test_prompt_processor.py    # Specific processor
pytest unit/core/                                   # All core tests
pytest unit/validators/                             # All validators

# Run by marker
pytest -m unit         # All unit tests
pytest -m integration  # All integration tests
pytest -m security     # All security tests

# Run by keyword
pytest -k "prompt"     # Tests matching "prompt"
pytest -k "validation" # Tests matching "validation"
```

## TDD Workflow

### Step 1: Pick Module & Find Tests
```bash
# Example: Implementing PromptProcessor
# Tests location: unit/processors/test_prompt_processor.py
# Tests: 036-046 (11 tests)

pytest unit/processors/test_prompt_processor.py -v
# All fail - not implemented yet
```

### Step 2: Implement Test-by-Test
```bash
# Create: app/processors/prompt_processor.py

# Run one test
pytest unit/processors/test_prompt_processor.py::test_036 -v

# Implement until it passes
# Repeat for each test
```

### Step 3: Verify Module
```bash
# All module tests should pass
pytest unit/processors/test_prompt_processor.py -v
```

### Step 4: Before Commit
```bash
# Run all unit tests
pytest unit/ -v

# Run with coverage
pytest unit/ --cov=app --cov-report=term
```

## Test Organization by Module

### Validators (unit/validators/) - 96 tests

**FlowValidator** - `test_flow_validator.py`
- Tests 001-035: Flow structure, triggers, wildcards, circular refs, orphans
- Tests 240-264: Interrupts, two-pass validation, dot notation
- Tests 291-295: Node name uniqueness

**InputValidator** - `test_input_validator.py`
- Tests 265-270: REGEX full string match (critical!)

**ConstraintValidator** - `test_constraint_validator.py`
- Tests 207-222: Content length limits (messages, patterns, templates)
- Tests 282-290: Position field validation

### Processors (unit/processors/) - 79 tests

**PromptProcessor** - `test_prompt_processor.py`
- Tests 036-046: Input collection, validation, retry logic
- Tests 141-152: Type conversion (string→number, boolean)

**MenuProcessor** - `test_menu_processor.py`
- Tests 047-055: STATIC/DYNAMIC menus, item templates
- Tests 234-239: Selection variable (auto-created, NUMBER type, 1-based)
- Tests 296-303: Selection range validation
- Tests 410-413: Error message customization
- Tests 423-424: Float selection handling

**APIActionProcessor** - `test_api_processor.py`
- Tests 056-063: API calls, error handling, response_map
- Tests 271-275: Body size limits (1 MB)
- Tests 276-281: Headers limit (10 max)
- Tests 414-422: All HTTP methods, 204 No Content
- Tests 434-438: Non-standard responses (3xx, 4xx, 5xx)

**LogicProcessor** - `test_logic_processor.py`
- Tests 064-066: Conditional routing only (no display)

**TextProcessor** - `test_text_processor.py`
- Tests 067-068: Display text, auto-progression
- Terminal nodes: Nodes without routes end the conversation

### Core Engine (unit/core/) - 88 tests

**SessionManager** - `test_session_manager.py`
- Tests 087-105: Lifecycle, 30-min timeout, termination, multi-bot isolation
- Tests 360-369: Flow snapshots (active sessions use original version)

**TemplateEngine** - `test_template_engine.py`
- Tests 070-086: Variable substitution ({{context.*}}, {{user.*}}, {{item.*}})

**RouteEvaluator** - `test_route_evaluator.py`
- Tests 106-120: First-match-wins, runtime sorting by priority

**ConditionEvaluator** - `test_condition_evaluator.py`
- Tests 153-168: Expression validation (input.isNumeric(), context access)
- Tests 425-428: String vs number (NO type coercion!)

**Orchestrator** - `test_orchestrator.py`
- Tests 169-175: Auto-progression (max 10 consecutive nodes)

### Utilities (unit/utils/) - 32 tests

**TypeConversion** - `test_type_conversion.py`
- Tests 141-152: String→number, string→boolean
- Tests 429-433: Array conversion edge cases

**TriggerMatching** - `test_trigger_matching.py`
- Tests 176-190: Exact standalone match, case-insensitive, multi-word

### Integration (integration/) - 37 tests
- Tests 131-140: Complete flow execution
- Tests 191-199: Route evaluation details
- Tests 200-206: Array truncation (24 items max)
- Tests 223-233: Retry logic end-to-end

### E2E (e2e/) - 30 tests
- Tests 439-440: Forms (multi-step collection)
- Tests 441-442: Surveys (branching questions)
- Tests 443: Bookings (date→time→location→confirm)
- Tests 444: E-commerce (browse→select→checkout)
- Tests 445: Support (issue→details→ticket)
- Tests 446: Onboarding (register→verify→setup)
- Tests 447-468: All conversation patterns

### Security (security/) - 50 tests
- Tests 121-130: Core security (ownership, webhooks, isolation)
- Tests 370-409: Security depth (sanitization, HTTPS, PII, audit logs)

### System (system/) - 112 tests
- Tests 304-329: Negative capabilities (what you CANNOT do)
- Tests 330-346: Error messages (exact text from spec)
- Tests 347-359: Bot management (entity, status, webhooks)
- Tests 469-489: Best practices (flow design, patterns)
- Tests 490-524: Core capabilities (multi-tenant, flow lifecycle)

## Critical Behaviors Tested

### REGEX Validation (Tests 265-270)
**CRITICAL**: Must match ENTIRE input, not substring
- Pattern `[0-9]+` for "123abc" → FAILS
- Pattern `^[0-9]+$` for "123" → PASSES
- Implicit anchors treated as /^pattern$/

### Type Conversion (Tests 141-152)
- **PROMPT**: Conversion failure → retry (counts toward max_attempts)
- **Mappings**: Conversion failure → null (no retry)
- NO type coercion: string "123" ≠ number 123

### Session Management (Tests 087-105, 360-369)
- Key format: "channel:channel_user_id:bot_id"
- **30-minute ABSOLUTE timeout** (not sliding window)
- Flow snapshots: Active sessions use original version
- Multi-bot isolation

### Routing (Tests 106-120, 191-199)
- Runtime sorting by priority
- First-match-wins
- NO type coercion in comparisons
- Null-safe evaluation

### Auto-Progression (Tests 169-175)
- Increments: TEXT, LOGIC_EXPRESSION, API_ACTION
- Resets: PROMPT, MENU (user input resets counter)
- Terminal: Nodes without routes end the conversation
- Max 10 consecutive → ERROR

### Interrupts (Tests 240-250)
- Checked BEFORE validation
- Case-insensitive, whitespace-trimmed
- Does NOT count as retry attempt
- Does NOT save to variable

### MENU Selection (Tests 234-239)
- selection variable auto-created (NUMBER type)
- 1-based indexing
- Set BEFORE output_mapping
- STATIC: max 8 options
- DYNAMIC: max 24 displayed

### Error Messages (Tests 330-346)
Exact text from spec:
- No route: "An error occurred. Please try again."
- Max auto-progression: "System error. Please contact support."
- Timeout: "Session expired. Please start again."
- Bot inactive: "Bot unavailable"
- Empty input: "This field is required. Please enter a value."

### Content Limits (Tests 207-222)
- Messages: 1024 chars
- Errors: 512 chars
- Patterns: 512 chars
- Templates: 1024 chars
- URLs: 1024 chars
- Headers: 10 max, names 128 chars, values 2048 chars

### API Constraints (Tests 271-281, 414-438)
- Body: 1 MB max (request & response)
- Timeout: 30 seconds (fixed)
- Methods: GET, POST, PUT, PATCH, DELETE
- 204 No Content supported
- JSON-only responses

## CI/CD Integration

```yaml
name: Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v --tb=short
      # Fast: 1-2 minutes

  integration:
    needs: unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/integration/ -v
      # Medium: 2-5 minutes

  e2e:
    needs: integration
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/e2e/ -v
      # Slow: 5-10 minutes
```

## Coverage Tracking

```bash
# All tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Unit tests only
pytest unit/ --cov=app --cov-report=term

# Specific module
pytest unit/processors/ --cov=app.processors --cov-report=term

# Generate HTML report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html
```

**Coverage Targets:**
- Unit: 90%+ code coverage
- Integration: 80%+ paths
- E2E: 100% critical journeys
- Overall: 85%+ combined

## Test Distribution by Spec Section

| Section | Tests |
|---------|-------|
| 0. System Architecture | 30 |
| 1. Flow Structure | 55 |
| 2. Core Capabilities | 70 |
| 3. System Constraints | 45 |
| 4. Node Types | 79 |
| 5. Templating | 23 |
| 6. Validation | 28 |
| 7. Routing & Logic | 28 |
| 8. Session Management | 30 |
| 9. Error Handling | 20 |
| 10. Security | 58 |
| 11. What You CAN Do | 42 |
| 12. What You CANNOT Do | 26 |
| 13. Best Practices | 30 |
| **Overall** | **524** |

## Status

✅ **524 tests implemented** - comprehensive specification coverage
✅ **TDD-optimized** - organized by implementation module
✅ **Comprehensive** - normal + error + edge cases
✅ **Well-documented** - clear descriptions, spec references
✅ **Speed-optimized** - fast feedback during development

**Ready for systematic TDD implementation!**
