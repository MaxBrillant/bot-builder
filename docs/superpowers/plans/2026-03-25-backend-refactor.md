# Backend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up backend code quality and architecture without changing any external behavior.

**Architecture:** Pure refactoring across 6 phases — dead code removal, file splits, processor cleanup, engine decomposition, template consolidation, and layer cleanup. Each phase is independently shippable.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Redis, Pydantic v2

**Spec:** `docs/superpowers/specs/2026-03-25-backend-refactor-design.md`

**Note:** Test files are out of scope. Verification is done by running the existing test suite after each task to confirm no regressions.

---

## Phase 1: Dead Code Removal and Consistency Fixes (Spec Section 6)

### Task 1: Remove dead code

**Files:**
- Modify: `backend/v1/app/core/redis_manager.py:139-201` (delete `_execute_with_circuit_breaker`)
- Delete: `backend/v1/app/core/validators.py`
- Modify: `backend/v1/app/utils/constants.py:134` (delete `MAX_MENU_OPTIONS`)

**Context:** `_execute_with_circuit_breaker` is defined but never called anywhere. `validators.py` is a 17-line thin re-export wrapper left from a previous refactor. `MAX_MENU_OPTIONS` is deprecated in favor of `MAX_STATIC_MENU_OPTIONS`.

- [ ] **Step 1:** Search codebase for any imports from `app.core.validators` and any calls to `_execute_with_circuit_breaker` to confirm they're unused or identify what needs updating.

Run: `cd backend/v1 && grep -rn "from app.core.validators" app/ && grep -rn "_execute_with_circuit_breaker" app/`

- [ ] **Step 2:** Update any imports that reference `app.core.validators` to import from `app.core.flow_validator` or `app.core.input_validator` directly.

- [ ] **Step 3:** Delete `_execute_with_circuit_breaker` method (lines 139-201) from `redis_manager.py`.

- [ ] **Step 4:** Delete `backend/v1/app/core/validators.py`.

- [ ] **Step 5:** Delete `MAX_MENU_OPTIONS` from `constants.py` (line 134). Search for any references first.

- [ ] **Step 6:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 7:** Commit.

```bash
git add -A && git commit -m "refactor: remove dead code - unused circuit breaker wrapper, validators shim, deprecated constant"
```

---

### Task 2: Establish Redis failure policy

**Files:**
- Modify: `backend/v1/app/core/redis_manager.py`

**Context:** Currently Redis methods are inconsistent — some caching operations raise exceptions (should fail-open) and some security operations silently continue (should fail-closed). The policy:
- Security operations (rate limiting, token blacklist): fail-closed (raise exception)
- Caching operations (flow cache, session cache, trigger cache): fail-open (return None, log warning)

- [ ] **Step 1:** Add a docstring at the top of `RedisManager` documenting the failure policy.

- [ ] **Step 2:** Audit each method. Security methods that should fail-closed: `check_rate_limit_channel_user` (line 403), `check_rate_limit_user` (line 430), `is_token_blacklisted` (line 666). Verify they all raise `SecurityServiceUnavailableError` when Redis is down.

- [ ] **Step 3:** Audit caching methods that should fail-open: `cache_flow` (line 205), `get_cached_flow` (line 249), `invalidate_flow_cache` (line 278), `cache_trigger_keyword` (line 297), `get_flows_by_keyword` (line 317), `cache_session` (line 477), `get_cached_session` (line 509). Verify they return None/empty and log warning (not raise) when Redis is down.

- [ ] **Step 4:** Fix any methods that don't match the policy.

- [ ] **Step 5:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 6:** Commit.

```bash
git add -A && git commit -m "refactor: establish and enforce Redis failure policy - fail-closed for security, fail-open for cache"
```

---

### Task 3: Consolidate exception hierarchy

**Files:**
- Modify: `backend/v1/app/utils/exceptions.py`

**Context:** 30+ exception classes, many near-identical. Keep base categories, collapse leaf classes into parameterized parents. Keep old class names as aliases so existing `except` blocks don't break.

Also fix bug: `MaxAutoProgressionError` is called with `limit=` kwarg but defined with `count=` parameter.

- [ ] **Step 1:** Read `exceptions.py` fully. Identify which leaf classes have genuinely different behavior (custom metadata fields beyond just a renamed parameter) vs which are structurally identical to their parent with just different default messages.

- [ ] **Step 2:** For each category, collapse near-identical classes. Keep classes that have unique metadata fields (e.g., `RedisUnavailableError` with `feature`, `CircularReferenceError` with `nodes` list). Collapse classes that only differ in default message text into their parent with a `type` parameter.

- [ ] **Step 3:** Create aliases for all collapsed classes so existing `except OldClassName` blocks still work:
Preferred approach: keep old names as thin subclasses with just a default message override. This is simpler and more debuggable than dynamic `type()` calls:
```python
class SessionExpiredError(SessionException):
    def __init__(self, message="Session expired", **kw):
        super().__init__(message, error_code="SESSION_EXPIRED", **kw)
```

- [ ] **Step 4:** Fix `MaxAutoProgressionError`: rename `count` parameter to `limit` to match actual usage in engine.py.

- [ ] **Step 5:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 6:** Commit.

```bash
git add -A && git commit -m "refactor: consolidate exception hierarchy, fix MaxAutoProgressionError parameter name"
```

---

### Task 4: Standardize logger patterns

**Files:**
- Modify: `backend/v1/app/processors/base_processor.py` (line 17 — remove module-level logger)
- Modify: `backend/v1/app/core/session_manager.py` (line 31 — remove module-level logger)
- Modify: Any other files with dual module+class loggers

**Context:** Some files create both a module-level `logger = get_logger(__name__)` AND a class-level `self.logger = get_logger(...)`. Pick one pattern: class-level for files with classes, module-level for files with only functions.

- [ ] **Step 1:** Search for all files with both patterns.

Run: `cd backend/v1 && grep -rln "^logger = get_logger" app/ | sort > /tmp/module_loggers.txt && grep -rln "self.logger = get_logger" app/ | sort > /tmp/class_loggers.txt && comm -12 /tmp/module_loggers.txt /tmp/class_loggers.txt`

- [ ] **Step 2:** For each file with both: if the module-level logger is used by module-level functions, keep it. If only the class logger is used, remove the module-level one. If both are used, convert module-level function calls to use a local logger or the class logger.

- [ ] **Step 3:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 4:** Commit.

```bash
git add -A && git commit -m "refactor: standardize logger patterns - one logger per file"
```

---

### Task 5: Standardize model to_dict() signatures

**Files:**
- Modify: `backend/v1/app/models/bot.py` (line 114)
- Modify: `backend/v1/app/models/flow.py` (line 83)
- Modify: `backend/v1/app/models/session.py` (line 199)
- Modify: `backend/v1/app/models/bot_integration.py` (line 84)

**Context:** Current signatures use inconsistent parameter names: `include_webhook_secret`, `include_integrations`, `include_definition`, `include_snapshot`, `include_config`. Standardize to consistent `include_` prefix pattern. The parameter names are already close — just ensure callers use the same pattern.

- [ ] **Step 1:** Search for all call sites of each `to_dict()` method to understand what parameters are passed.

- [ ] **Step 2:** Standardize parameter names if any are inconsistent. Update all call sites.

- [ ] **Step 3:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 4:** Commit.

```bash
git add -A && git commit -m "refactor: standardize model to_dict() parameter naming"
```

---

### Task 6: Create error response helper

**Files:**
- Create: `backend/v1/app/utils/responses.py`
- Modify: API endpoint files that construct error dicts inline

**Context:** Endpoints construct error response dicts with different structures. Create a small helper function that standardizes the format. Not middleware — just a function.

- [ ] **Step 1:** Search for common error response patterns across API files.

Run: `cd backend/v1 && grep -rn "raise HTTPException" app/api/ | head -30`

- [ ] **Step 2:** Create `utils/responses.py` with a helper that returns standardized error responses.

- [ ] **Step 3:** Update all endpoints that construct error response dicts inline to use the helper. Sweep through all API files: `auth.py`, `bots.py`, `flows.py`, `webhooks/core.py`, `webhooks/whatsapp.py`.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: add error response helper for consistent API error formatting"
```

---

## Phase 2: Mixed-Concern File Splits (Spec Section 4)

### Task 7: Split security.py into security/ package

**Files:**
- Delete: `backend/v1/app/utils/security.py`
- Create: `backend/v1/app/utils/security/__init__.py` (re-exports)
- Create: `backend/v1/app/utils/security/password.py` (lines 17-69 from old security.py)
- Create: `backend/v1/app/utils/security/sanitization.py` (lines 171-342 from old security.py)
- Create: `backend/v1/app/utils/security/ssrf.py` (lines 345-491 from old security.py)

**Context:** security.py mixes 4 concerns. JWT operations (lines 72-168) stay in `__init__.py` since they're small and tightly coupled to auth. Fix the `}` regex bug in sanitization.py (line 280).

- [ ] **Step 1:** Read `security.py` fully. Note exact line ranges for each concern.

- [ ] **Step 2:** Create `backend/v1/app/utils/security/` directory.

- [ ] **Step 3:** Create `password.py` with `verify_password()`, `get_password_hash()`.

- [ ] **Step 4:** Create `sanitization.py` with `sanitize_input()`, `check_suspicious_patterns()`, `escape_html()`, `SanitizationError`. Fix the `}` regex: change `r'\}'` (line 280) to `r'\$\{[^}]*\}'`.

- [ ] **Step 5:** Create `ssrf.py` with `BLOCKED_IP_NETWORKS`, `is_safe_url_for_ssrf()`, `validate_node_id_format()`, `generate_session_id()`.

- [ ] **Step 6:** Create `__init__.py` with JWT functions (`create_access_token`, `decode_access_token`, `extract_user_id_from_token`, `create_refresh_token`) and re-exports from all submodules so `from app.utils.security import sanitize_input` still works.

- [ ] **Step 7:** Delete old `security.py`.

- [ ] **Step 8:** Verify all imports still resolve.

Run: `cd backend/v1 && python -c "from app.utils.security import sanitize_input, verify_password, is_safe_url_for_ssrf, create_access_token; print('OK')"`

- [ ] **Step 9:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 10:** Commit.

```bash
git add -A && git commit -m "refactor: split security.py into security/ package, fix template injection regex"
```

---

### Task 8: Split constants.py into constants/ package

**Files:**
- Delete: `backend/v1/app/utils/constants.py`
- Create: `backend/v1/app/utils/constants/__init__.py` (re-exports)
- Create: `backend/v1/app/utils/constants/enums.py` (lines 10-94)
- Create: `backend/v1/app/utils/constants/constraints.py` (lines 98-154)
- Create: `backend/v1/app/utils/constants/patterns.py` (lines 158-237)

- [ ] **Step 1:** Read `constants.py` fully.

- [ ] **Step 2:** Create `backend/v1/app/utils/constants/` directory.

- [ ] **Step 3:** Create `enums.py` with all enum classes: NodeType, SessionStatus, BotStatus, IntegrationStatus, OAuthProvider, ValidationType, MenuSourceType, HTTPMethod, IntegrationPlatform, VariableType, RouteCondition.

- [ ] **Step 4:** Create `constraints.py` with SystemConstraints class.

- [ ] **Step 5:** Create `patterns.py` with SpecialVariables, ErrorMessages, RegexPatterns, RouteValidationRules, ReservedKeywords.

- [ ] **Step 6:** Create `__init__.py` that re-exports everything from all submodules.

- [ ] **Step 7:** Delete old `constants.py`.

- [ ] **Step 8:** Verify imports resolve.

Run: `cd backend/v1 && python -c "from app.utils.constants import NodeType, SystemConstraints, RegexPatterns; print('OK')"`

- [ ] **Step 9:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 10:** Commit.

```bash
git add -A && git commit -m "refactor: split constants.py into constants/ package"
```

---

### Task 9: Decompose flow_validator.validate_flow god method

**Files:**
- Modify: `backend/v1/app/core/flow_validator.py:394-525`

**Context:** `validate_flow` is 130+ lines doing 15 validations. Break into focused private methods. Also batch the keyword duplicate DB check into a single query.

- [ ] **Step 1:** Read `flow_validator.py` fully. Map each validation step in `validate_flow` (lines 394-525).

- [ ] **Step 2:** Extract each validation step into a private method:
  - `_validate_flow_metadata(flow_data, errors)` — required fields, flow name
  - `_validate_trigger_keywords(flow_data, bot_id, errors)` — keyword format, length, uniqueness
  - `_validate_flow_variables(flow_data, errors)` — variable definitions
  - `_validate_node_structure(flow_data, errors)` — node count, parsing, Pydantic validation
  - `_validate_node_graph(nodes, flow_data, errors)` — start node, orphans, cycles, unreachable
  - `_validate_routes(nodes, errors)` — route conditions, targets

- [ ] **Step 3:** Rewrite `validate_flow` as an orchestrator that calls each method in sequence, collecting errors.

- [ ] **Step 4:** Batch the keyword duplicate check: instead of N sequential queries (one per keyword), do a single query that checks all keywords at once.

- [ ] **Step 5:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 6:** Commit.

```bash
git add -A && git commit -m "refactor: decompose flow_validator.validate_flow into focused methods, batch keyword check"
```

---

## Phase 3: Processor Copy-Paste Cleanup (Spec Section 1)

### Task 10: Add shared terminal/no-route methods to BaseProcessor

**Files:**
- Modify: `backend/v1/app/processors/base_processor.py`

- [ ] **Step 1:** Read `base_processor.py` fully.

- [ ] **Step 2:** Add `check_terminal(node, context, message=None)` method that returns a terminal `ProcessResult` if node has no routes, or `None` if it does. This replaces the "has_routes" check duplicated across all 6 processors.

```python
def check_terminal(self, node, context: dict, message: str = None) -> Optional[ProcessResult]:
    if node.routes and len(node.routes) > 0:
        return None
    self.logger.debug(f"{node.type} node '{node.id}' has no routes - terminal node", node_id=node.id)
    return ProcessResult(message=message, next_node=None, context=context)
```

- [ ] **Step 3:** Add `raise_no_matching_route(node)` method that raises `NoMatchingRouteError`. This replaces the 3 duplicate blocks in logic/text/set_variable processors.

```python
def raise_no_matching_route(self, node) -> None:
    self.logger.error(f"No matching route in {node.type} node '{node.id}'", node_id=node.id)
    raise NoMatchingRouteError(f"No route condition matched in {node.type} node '{node.id}'", node_id=node.id)
```

- [ ] **Step 4:** Verify no regressions (adding methods doesn't break anything).

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: add shared terminal/no-route methods to BaseProcessor"
```

---

### Task 11: Inject SessionManager into processors via factory

**Files:**
- Modify: `backend/v1/app/processors/factory.py`
- Modify: `backend/v1/app/processors/base_processor.py`

**Context:** SessionManager is instantiated inline 6+ times across prompt and menu processors. Instead, inject it via the factory.

- [ ] **Step 1:** Add `session_manager` as an optional parameter to `BaseProcessor.__init__` and store as `self.session_manager`.

- [ ] **Step 2:** Add `session_manager` parameter to `ProcessorFactory.__init__`. Pass it through to all processor instantiations in `_instantiate_processor`.

- [ ] **Step 3:** Update engine.py where ProcessorFactory is created to pass the SessionManager instance.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: inject SessionManager into processors via factory"
```

---

### Task 12: Update all 6 processors to use shared base methods

**Files:**
- Modify: `backend/v1/app/processors/prompt_processor.py`
- Modify: `backend/v1/app/processors/menu_processor.py`
- Modify: `backend/v1/app/processors/api_action_processor.py`
- Modify: `backend/v1/app/processors/logic_processor.py`
- Modify: `backend/v1/app/processors/text_processor.py`
- Modify: `backend/v1/app/processors/set_variable_processor.py`

- [ ] **Step 1:** In each processor, replace the "has_routes" terminal check block with:
```python
terminal = self.check_terminal(node, context, message=message)  # message only for text_processor
if terminal:
    return terminal
```

- [ ] **Step 2:** In logic, text, and set_variable processors, replace the "no matching route" error block with:
```python
if next_node is None:
    self.raise_no_matching_route(node)
```

- [ ] **Step 3:** In prompt and menu processors, remove all inline `from app.core.session_manager import SessionManager` / `SessionManager(db)` patterns. Use `self.session_manager` instead.

- [ ] **Step 4:** In menu_processor, extract duplicated source array truncation into a private method `_truncate_source_array()`.

- [ ] **Step 5:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 6:** Commit.

```bash
git add -A && git commit -m "refactor: replace duplicated processor patterns with shared base methods"
```

---

### Task 13: Consolidate retry logic in prompt_processor

**Files:**
- Modify: `backend/v1/app/processors/prompt_processor.py`

**Context:** prompt_processor has 4 duplicated retry/validation failure blocks. RetryHandler already exists but isn't used for all retry paths.

- [ ] **Step 1:** Read prompt_processor.py fully. Identify all 4 retry blocks.

- [ ] **Step 2:** Ensure RetryHandler is instantiated once (using injected SessionManager) and used for all validation failure paths.

- [ ] **Step 3:** Replace each duplicated retry block with a call to RetryHandler.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: consolidate prompt_processor retry logic via RetryHandler"
```

---

## Phase 4: Engine God Method Decomposition (Spec Section 2)

### Task 14: Define callback constants and extract error response helper

**Files:**
- Modify: `backend/v1/app/core/engine.py`

- [ ] **Step 1:** Add module-level constants:
```python
IS_INTERMEDIATE = False
IS_FINAL = True
```

- [ ] **Step 2:** Replace all bare `True`/`False` in `message_callback` invocations (6 locations) with these constants.

- [ ] **Step 3:** Extract `_build_error_response(session, error_message)` and `_build_response(session, messages, active, ended)` private methods on FlowExecutor. Replace all duplicated response dict constructions.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: add callback constants and extract response builder in engine"
```

---

### Task 15: Extract helper methods from execute_flow

**Files:**
- Modify: `backend/v1/app/core/engine.py`

- [ ] **Step 1:** Extract `_update_message_history(session, message, sender, node_id, extra=None)` that appends to history and truncates to 50. Replace all 3 message history blocks (lines ~254-267, ~399-412, ~491-504).

- [ ] **Step 2:** Extract `_inject_user_context(node_type, context, user_context)` that returns enhanced context for API_ACTION nodes or plain context otherwise. Also handles removing `user` key from result context. Replace inline block (lines ~352-376).

- [ ] **Step 3:** Extract `_handle_terminal(session, result, messages, message_callback)` that handles session completion and final callback for terminal nodes.

- [ ] **Step 4:** Extract `_process_single_node(session, node, nodes, flow_variables, user_input, user_context)` — gets processor from factory, injects user context, invokes processor, cleans up user context from result. This is the core dispatch logic currently inline in the loop.

- [ ] **Step 5:** The remaining `execute_flow` should be a readable loop of ~50-80 lines.

- [ ] **Step 6:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 7:** Commit.

```bash
git add -A && git commit -m "refactor: decompose execute_flow into focused helper methods"
```

---

## Phase 5: Template Engine Rendering Consolidation (Spec Section 3)

### Task 16: Extract shared rendering logic

**Files:**
- Modify: `backend/v1/app/core/template_engine.py`

- [ ] **Step 1:** Read template_engine.py fully. Map the shared logic across `render()`, `render_url()`, `render_html()`, `render_counter()`.

- [ ] **Step 2:** Extract `_render_internal(context, template, formatter, skip_validation=False)`:
  - Contains: regex matching, variable extraction, path resolution, null handling, value formatting
  - `formatter` parameter: callable that transforms the resolved value to string (e.g., `str`, `html.escape`, `urllib.parse.quote`)
  - `skip_validation`: True for `render_counter` which uses permissive mode

- [ ] **Step 3:** Rewrite each public method as a thin wrapper:
```python
def render(self, context, template):
    return self._render_internal(context, template, formatter=self._format_value)

def render_url(self, context, template):
    return self._render_internal(context, template, formatter=lambda v: quote(str(v), safe=''))

def render_html(self, context, template):
    return self._render_internal(context, template, formatter=lambda v: escape_html(str(v)))

def render_counter(self, counter_context, template):
    return self._render_internal(counter_context, template, formatter=self._format_value, skip_validation=True)
```

- [ ] **Step 4:** `render_json_value()` stays untouched — it has different logic.

- [ ] **Step 5:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 6:** Commit.

```bash
git add -A && git commit -m "refactor: consolidate template engine rendering into shared _render_internal"
```

---

## Phase 6: Layer Cleanup (Spec Section 5)

### Task 17: Move cache invalidation into RedisManager

**Files:**
- Modify: `backend/v1/app/core/redis_manager.py`
- Modify: `backend/v1/app/services/flow_service.py`

- [ ] **Step 1:** Add `invalidate_flow_and_triggers(flow_id, keywords, bot_id)` to RedisManager that handles all cache key construction and invalidation internally.

- [ ] **Step 2:** Replace direct cache key manipulation in FlowService (lines ~294-304) with a single call to `redis_manager.invalidate_flow_and_triggers(...)`.

- [ ] **Step 3:** Similarly simplify the cache deserialization pattern — extract `_flow_from_cache(cached)` in FlowService to remove the duplication between `get_flow` and `get_flow_by_id_only`.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: move cache invalidation logic into RedisManager"
```

---

### Task 18: Move bot response assembly out of API layer

**Files:**
- Modify: `backend/v1/app/api/bots.py:29-66`
- Modify: `backend/v1/app/models/bot.py`

- [ ] **Step 1:** Move `bot_to_response()` logic into a `to_response()` method on the Bot model. It knows about its own integrations — this is domain logic, not API logic.

- [ ] **Step 2:** Update all call sites in `bots.py` to use `bot.to_response(include_secret=...)` instead of the standalone function.

- [ ] **Step 3:** Delete the old `bot_to_response()` function from `bots.py`.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: move bot response assembly into Bot model"
```

---

### Task 19: Extract shared webhook sanitization

**Files:**
- Create: `backend/v1/app/api/webhooks/sanitization.py`
- Modify: `backend/v1/app/api/webhooks/core.py:163-228`
- Modify: `backend/v1/app/api/webhooks/whatsapp.py:118-156`

- [ ] **Step 1:** Create `sanitization.py` with a function `sanitize_and_audit_webhook_input(message, audit_log, logger)` that encapsulates the shared sanitization + suspicious pattern check + audit logging.

- [ ] **Step 2:** Replace the duplicated blocks in `core.py` and `whatsapp.py` with calls to this function.

- [ ] **Step 3:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 4:** Commit.

```bash
git add -A && git commit -m "refactor: extract shared webhook sanitization logic"
```

---

### Task 20: Extract shared schema validation and delete OwnershipChecker

**Files:**
- Modify: `backend/v1/app/schemas/flow_schema.py`
- Modify: `backend/v1/app/api/middleware.py:41-207`

- [ ] **Step 1:** Extract trigger keyword validation into a standalone function in `flow_schema.py`:
```python
def _validate_trigger_keyword_list(keywords: List[str]) -> List[str]:
    # shared validation logic
```

- [ ] **Step 2:** Update both `FlowCreate` and `FlowUpdate` field validators to call this function.

- [ ] **Step 3:** Delete `OwnershipChecker` class from `middleware.py` (lines 41-207). It's never used.

- [ ] **Step 4:** Verify no regressions.

Run: `cd backend/v1 && python -m pytest tests/ -x -q 2>&1 | tail -20`

- [ ] **Step 5:** Commit.

```bash
git add -A && git commit -m "refactor: extract shared keyword validation, delete unused OwnershipChecker"
```
