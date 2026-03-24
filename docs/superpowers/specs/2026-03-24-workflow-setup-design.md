# Workflow Setup Design

**Date:** 2026-03-24
**Status:** Approved

## Problem

The project had no enforced development workflow. CLAUDE.md was outdated, verbose, and contained no guidance aligned with the Superpowers skill system. There was no docs structure for specs or plans. Future work had nowhere to land.

## Goal

Establish a lean CLAUDE.md and a `docs/` scaffold so that:
- Claude sessions start with the right context (critical constraints, key paths, dev commands)
- Superpowers workflow artifacts (specs, plans) have a defined home
- Architecture knowledge is preserved and accessible but not cluttering the session context

## Approach

Approach B: CLAUDE.md rewrite + docs scaffold. Chosen over A (CLAUDE.md only — no artifact home) and C (full content migration — YAGNI).

## Deliverables

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Lean session context: project summary, key paths, dev commands, critical constraints, git conventions |
| `docs/project/architecture.md` | Backend architecture knowledge extracted from old CLAUDE.md |
| `docs/project/README.md` | Index of project docs |
| `docs/superpowers/specs/README.md` | Naming convention and purpose for spec files |
| `docs/superpowers/plans/README.md` | Naming convention and purpose for plan files |

## What Was Removed from CLAUDE.md

- "Core Rules" (Always Ask Questions, Criticize Everything, etc.) — covered by Superpowers skills
- "Development Workflow" 5-step process — covered by Superpowers skills
- Full architecture prose — moved to `docs/project/architecture.md`
- Frontend architecture section — out of scope for backend focus
- Dependency lists — already in `requirements.txt` and `package.json`
- Security notes — either obvious or covered in BOT_BUILDER_SPECIFICATIONS.md

## What Was Kept

- Critical constraints not obvious from code (Redis mandatory, template syntax gotchas, session timeout)
- Key file paths with notes on known issues (files that need splitting)
- Dev commands (run, test, migrate)
- Git commit conventions

## Out of Scope

- No hooks or settings.json changes
- No backend code changes
- No frontend changes
- Backend architecture refactoring is a separate sub-project
