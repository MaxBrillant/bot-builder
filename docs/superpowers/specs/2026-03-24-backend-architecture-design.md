# Backend Architecture Design

**Date:** 2026-03-24
**Status:** Approved

## Problem

Three backend files have grown beyond a readable size, making them hard to navigate and reason about:

- `app/core/validators.py` — 1536 lines, 4 classes serving different callsites
- `app/core/redis_manager.py` — 1019 lines, `DistributedCircuitBreaker` buried inside connection management
- `app/models/node_configs.py` — 1036 lines, but internally coherent (one domain, 6 node types) — left alone

## Goal

Split oversized files into focused modules with single responsibilities, without changing any logic or breaking any existing imports.

## Approach

Approach A: Minimal split. Extract natural boundaries that already exist in the code. Backward-compat shims preserve all existing import sites.

Rejected: Splitting `RedisManager` into per-concern service classes (Approach B/C) — all 6 concerns share one connection with circuit breaker and reconnect logic; splitting creates more coupling, not less.

Rejected: Splitting `node_configs.py` — it's one coherent domain (Pydantic models for flow definitions). Size is justified by 6 node types, not mixed concerns.

## File Changes

### validators.py split

**Before:** `app/core/validators.py` (1536 lines) — InputValidator, RouteConditionValidator, ValidationResult, FlowValidator

**After:**

| File | Contents | Lines | Used by |
|------|----------|-------|---------|
| `app/core/input_validator.py` | `InputValidator` only | ~150 | processors (runtime input checking) |
| `app/core/flow_validator.py` | `FlowValidator` + `RouteConditionValidator` + `ValidationResult` | ~400 | flow_service (submit-time structure checking) |
| `app/core/validators.py` | Thin re-export shim + `ValidationSystem = InputValidator` alias | ~10 | existing import sites (unchanged) |

### redis_manager.py split

**Before:** `app/core/redis_manager.py` (1019 lines) — CircuitState, DistributedCircuitBreaker, RedisManager

**After:**

| File | Contents | Lines | Used by |
|------|----------|-------|---------|
| `app/core/circuit_breaker.py` | `CircuitState` + `DistributedCircuitBreaker` + `CircuitBreaker` alias | ~280 | redis_manager.py |
| `app/core/redis_manager.py` | `RedisManager` only, imports from circuit_breaker.py | ~700 | app-wide (unchanged import path) |

`circuit_breaker.py` has no dependency on `RedisManager` or app config — accepts a redis client via `set_redis()`.

## Constraints

- Zero logic changes — pure file reorganization
- All existing import sites continue working unchanged
- All existing tests pass without modification
- No new tests required (no new logic)

## Commit Strategy

Two commits:
1. `refactor: split validators.py into input_validator and flow_validator`
2. `refactor: extract circuit_breaker from redis_manager`

## Out of Scope

- `node_configs.py` — not touched
- Any processor files — not touched
- `engine.py`, `session_manager.py`, `conditions.py`, `template_engine.py` — not touched
- Frontend — not in scope
- No new abstractions, interfaces, or patterns introduced
