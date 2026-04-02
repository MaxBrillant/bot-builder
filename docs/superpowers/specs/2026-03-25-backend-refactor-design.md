# Backend Refactor Design Spec

**Date:** 2026-03-25
**Type:** Pure refactoring — no feature or behavior changes
**Scope:** Backend internal code quality and architecture cleanup
**External contracts preserved:** All API routes, webhook formats, DB schema, SSE streaming, error messages to clients

---

## Problem

The backend grew organically and accumulated:
- Copy-pasted logic across processors, webhooks, schemas, and services
- God methods in engine.py (300+ lines) and flow_validator.py (130+ lines)
- Mixed concerns in utility files (security.py has 4 unrelated responsibilities, constants.py has 7)
- Business logic in the wrong layer (cache management in services, response assembly in routers)
- Dead code left from previous refactors
- Inconsistent patterns for error handling, Redis failure modes, logging, and model serialization
- Over-engineered exception hierarchy (30+ near-identical classes)

## Approach

Module restructure with surgical cleanup. Keep all external interfaces identical. Break work into 6 independent sections that can be implemented and verified in sequence.

## Constraints

- Same inputs produce same outputs everywhere
- All API routes, webhook contracts, SSE streaming behavior unchanged
- DB schema unchanged, no migrations
- No feature additions or removals
- Test files are out of scope (will be addressed separately later)
- One known bug fixed: `}` regex in security.py that blocks all closing braces

---

## Section 1: Processor Copy-Paste Cleanup

### Problem
All 6 processors repeat identical patterns:
- "has_routes" terminal check (6 identical blocks across prompt, menu, api_action, logic, text, set_variable processors)
- "no matching route" error handling (3 identical blocks in logic, text, set_variable)
- `SessionManager` instantiated inline 10+ times across prompt and menu processors instead of injected
- Retry/validation failure handling duplicated 4x in prompt_processor

### Changes

**base_processor.py:**
- Add `handle_terminal(node)` concrete method — encapsulates the "no routes = terminal node" check that all processors duplicate. Returns a terminal `ProcessResult` or `None` if node has routes.
- Add `handle_no_matching_route(node)` concrete method — encapsulates the "evaluated all routes, none matched" error. Returns an error `ProcessResult`.

**factory.py:**
- Inject `SessionManager` instance into processors via factory. Processors receive it in `__init__` instead of constructing it per-method.
- `SessionManager` constructed once per factory (same pattern as existing processor caching).

**All 6 processors:**
- Replace inline "has_routes" blocks with `self.handle_terminal(node)` call
- Replace inline "no matching route" blocks with `self.handle_no_matching_route(node)` call

**prompt_processor.py:**
- Remove inline `SessionManager` construction (use injected instance)
- Consolidate the 4 duplicated retry/validation failure blocks into calls to `RetryHandler` (which already exists but isn't used for all retry paths)

**menu_processor.py:**
- Remove inline `SessionManager` construction (use injected instance)
- Extract duplicated source array truncation into a private method

### Verification
Each processor produces identical `ProcessResult` for identical inputs. The factory creates the same processor types with the same capabilities.

---

## Section 2: Engine God Method Decomposition

### Problem
`FlowExecutor.execute_flow` is 300+ lines doing 15 distinct things. Message history truncation happens twice. Error response dicts are copy-pasted 4x. The `message_callback` second boolean parameter (`True`/`False`) is undocumented.

### Changes

**engine.py — FlowExecutor:**
- Extract `_build_error_response(session, error_message)` — replaces the 4 duplicated error response dict constructions
- Extract `_process_single_node(session, node, nodes, flow_variables)` — get processor from factory, invoke, return result. Contains the processor dispatch logic currently inline in the loop.
- Extract `_update_message_history(session, message, role)` — append message and truncate to 50 items. Called once per message, not twice.
- Extract `_inject_user_context(session, node_type, context)` — the API_ACTION-specific `user.channel_id` and `user.channel` injection, currently inline
- Extract `_handle_terminal(session, result, message_callback)` — terminal detection, session completion, final callback

**engine.py — message_callback clarity:**
- Define module-level constants for the callback's boolean: `IS_INTERMEDIATE = False`, `IS_FINAL = True`. Replace bare `True`/`False` in all callback invocations. Constants are sufficient — no enum needed for a two-value boolean.

**engine.py — main loop:**
The remaining `execute_flow` becomes a readable loop:
```
while not terminal and auto_progression < max:
    node = get current node
    result = _process_single_node(...)
    _update_message_history(...)
    if result.terminal: return _handle_terminal(...)
    if result.needs_input: commit and return
    advance to next node
```

### Verification
Same flow execution order, same auto-progression counting, same state transitions, same messages sent via callback in same order.

---

## Section 3: Template Engine Rendering Consolidation

### Problem
`render()`, `render_url()`, `render_html()`, and `render_counter()` are 4 near-identical methods (~200 lines total). They differ only in how the final value is formatted.

### Changes

**template_engine.py:**
- Extract `_render_internal(context, template, formatter)` containing the shared logic: regex matching, variable extraction, dot notation resolution, null/missing variable handling
- `render()` calls `_render_internal(context, template, formatter=str)`
- `render_url()` calls `_render_internal(context, template, formatter=urllib.parse.quote)`
- `render_html()` calls `_render_internal(context, template, formatter=html.escape)`
- `render_counter()` calls `_render_internal(counter_context, template, formatter=str)` with its counter-specific context preparation done before the call
- `render_json_value()` stays separate — it has genuinely different logic (type preservation vs string output)

### Verification
Same templates produce same output strings for all four rendering modes.

---

## Section 4: Mixed-Concern File Splits

### Problem
- `security.py` mixes password hashing, JWT operations, input sanitization, and SSRF validation
- `constants.py` mixes enums, system constraints, special variables, error messages, regex patterns, and reserved keywords
- `flow_validator.py` has a 130-line `validate_flow` god method doing 15 unrelated validations

### Changes

**security.py -> security/ package:**
- `security/__init__.py` — re-exports everything for backward-compatible imports
- `security/password.py` — `hash_password()`, `verify_password()`
- `security/sanitization.py` — `sanitize_input()`, suspicious pattern detection. Fix: change `r'\}'` pattern to `r'\$\{[^}]*\}'` to match template injection specifically instead of blocking all closing braces.
- `security/ssrf.py` — `validate_url()`, private IP detection, SSRF checks
- JWT operations stay in `security/__init__.py` (tightly coupled to auth, small surface area)

**constants.py -> constants/ package:**
- `constants/__init__.py` — re-exports everything for backward-compatible imports
- `constants/enums.py` — NodeType, SessionStatus, BotStatus, ValidationType, RouteCondition, etc.
- `constants/constraints.py` — SystemConstraints class with all limits
- `constants/patterns.py` — RegexPatterns, SpecialVariables, ReservedKeywords, ErrorMessages

**flow_validator.py — method decomposition:**
- Break `validate_flow` into focused private methods called in sequence:
  - `_validate_flow_metadata(flow_data)` — name, required fields
  - `_validate_trigger_keywords(flow_data, bot_id)` — keyword format, length, uniqueness
  - `_validate_flow_variables(flow_data)` — variable definitions, defaults
  - `_validate_node_structure(flow_data)` — node count, node parsing, Pydantic validation
  - `_validate_node_graph(nodes)` — start node, orphans, cycles, unreachable nodes
  - `_validate_routes(nodes)` — route conditions, targets, duplicates
- The public `validate_flow` orchestrates them in order, collecting errors
- Also: batch the keyword duplicate database check into a single query instead of N sequential queries

### Verification
Same validation errors returned for same invalid flows. Same security checks applied (except `}` bugfix). Same constants available at same import paths via re-exports.

---

## Section 5: Layer Cleanup

### Problem
- `FlowService` directly manages Redis cache keys and invalidation (infrastructure in business logic)
- `api/bots.py` has `bot_to_response()` assembling WhatsApp integration status (domain logic in API layer)
- `OwnershipChecker` class exists in middleware.py but is never used
- Both webhook handlers duplicate 65 lines of input sanitization + audit logging
- `FlowCreate` and `FlowUpdate` schemas duplicate 50 lines of trigger keyword validation

### Changes

**Cache invalidation:**
- Move cache key knowledge into `RedisManager`. Add method `invalidate_flow_and_triggers(flow_id, keywords, bot_id)` that handles all cache key construction internally.
- `FlowService` calls `redis_manager.invalidate_flow_and_triggers(flow)` — doesn't know about cache key structure.

**Bot response assembly:**
- Move `bot_to_response()` logic into a `to_response()` method on the `Bot` model or into `BotService`. The router calls it without knowing about integration status extraction.

**Dead abstraction:**
- Delete `OwnershipChecker` from middleware.py. The inline ownership pattern in endpoints is simpler and already consistent.

**Webhook sanitization:**
- Extract shared sanitization + audit logging into a function (e.g., `sanitize_and_audit_webhook_input(message, audit_log, logger)`) in a shared location. Both webhook handlers call it.

**Schema validation:**
- Extract trigger keyword validation into a standalone function `validate_trigger_keywords(keywords: List[str]) -> List[str]`. Both `FlowCreate` and `FlowUpdate` call it from their field validators.

### Verification
Same API responses, same cache invalidation behavior, same sanitization applied, same validation errors.

---

## Section 6: Dead Code Removal and Consistency Fixes

### Problem
- `_execute_with_circuit_breaker` in redis_manager.py never called
- `validators.py` thin wrapper left from previous refactor (17 lines, just re-exports)
- Inconsistent Redis failure handling (fail-open vs fail-closed mixed without policy)
- Inconsistent error response formats across endpoints
- Module-level AND class-level loggers in same files
- Inconsistent `to_dict()` parameter naming across models
- 30+ exception classes with near-identical implementations

### Changes

**Dead code removal:**
- Delete `_execute_with_circuit_breaker` from redis_manager.py
- Delete `validators.py` — update any remaining imports to point to `flow_validator` or `input_validator` directly
- Delete deprecated `MAX_MENU_OPTIONS` constant (replaced by `MAX_STATIC_MENU_OPTIONS`)
- Remove `OwnershipChecker` (covered in Section 5)

**Redis failure policy:**
- Document policy at top of `RedisManager`:
  - Security operations (rate limiting, token blacklist): fail-closed (raise exception)
  - Caching operations (flow cache, session cache, trigger cache): fail-open (return None, log warning)
- Audit all methods to match this policy. Currently some caching methods raise exceptions and some security methods silently continue — make them consistent.

**Error response consistency:**
- Create a small helper function `error_response(status_code, message, error_code=None)` that all endpoints use. Not middleware, just a function that returns the standard dict format. Endpoints call it instead of constructing dicts inline with different structures.

**Logger consistency:**
- Use class-level logger pattern everywhere: `self.logger = get_logger(self.__class__.__name__)`
- Remove module-level `logger = get_logger(__name__)` from files that also create class loggers
- For files with only module-level functions (no classes), keep module-level logger

**Model serialization consistency:**
- Standardize `to_dict()` across all models: use `include_` prefix for optional sections consistently (e.g., `include_secret`, `include_config`, `include_definition`, `include_snapshot`)

**Exception hierarchy consolidation:**
- Keep base categories: `BotBuilderError`, `SessionException`, `ValidationException`, `ExecutionException`, `AuthenticationException`, `SecurityException`
- Collapse near-identical leaf classes into parameterized parents. For example:
  - `SessionExpiredError`, `SessionNotFoundError`, `SessionLockError` → `SessionException(error_type="expired"|"not_found"|"locked")` with default messages per type
  - Keep distinct classes only where they have genuinely different behavior or metadata fields
- Keep old class names as aliases (e.g., `SessionExpiredError = SessionException.expired`) so existing `except SessionExpiredError` catch blocks across the codebase continue to work without rewriting. Remove aliases only after all catch sites are migrated.
- Preserve all error codes and default messages so client-facing errors don't change

### Verification
Same errors raised with same error codes and messages. Same Redis behavior (just documented and made consistent). Same model dict output. Same log content (different logger names in some cases, but same messages).

---

## Implementation Order

Sections are ordered by dependency:

1. **Section 6** (dead code + consistency) — removes noise, establishes patterns that later sections follow
2. **Section 4** (file splits) — creates the module structure that later sections work within
3. **Section 1** (processor cleanup) — depends on consistent patterns from Section 6
4. **Section 2** (engine decomposition) — depends on cleaner processors from Section 1
5. **Section 3** (template engine) — independent, can slot anywhere after Section 6
6. **Section 5** (layer cleanup) — touches multiple layers, easiest to do last when other sections have cleaned up internals

Each section is independently shippable and verifiable.
