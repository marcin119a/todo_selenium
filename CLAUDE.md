# CLAUDE.md


This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
venv/bin/pytest

# Run a single test file
venv/bin/pytest test_auth.py

# Run a single test by name
venv/bin/pytest test_tasks.py::TestAddTask::test_add_task_appears_on_list

# Run with verbose output
venv/bin/pytest -v

# Run with stdout visible (useful for debugging)
venv/bin/pytest -s
```

## Prerequisites

The frontend app must be running at `http://localhost:5173` before tests execute. The backend auth endpoint is also expected at `http://localhost:5173/auth/login`.

The test suite uses a pre-existing account (`marcin119a@gmail.com` / `string`) defined in `conftest.py`.

## Architecture

This is a Selenium E2E test suite for a todo web app (React/Vue frontend, JWT auth).

**`conftest.py`** — shared fixtures:
- `driver` — fresh Chrome session per test, implicit wait 8s, auto-quits
- `driver_logged_in` — driver with auth token injected directly into `localStorage` (bypasses UI login for speed)
- `screenshot_on_failure` — auto-captures screenshot to `screenshots/<test_nodeid>/screenshot.png` on failure

**Test files:**
- `test_auth.py` — registration, login, logout, session persistence via localStorage
- `test_tasks.py` — CRUD operations (add/edit/delete) and status toggle; cleanup fixture removes test tasks after each test
- `test_deadlines.py` — due date setting/clearing, overdue filter, AI priority suggestions, upcoming (7-day) filter

**Key patterns:**
- Date inputs are set via `driver.execute_script` + synthetic `input`/`change` events (required for React/Vue reactivity)
- `window.confirm` is overridden via JS to control delete confirmations
- Auth token flow: POST to `/auth/login` → extract `access_token` → inject into `localStorage`
- CSS selectors use multiple fallbacks (e.g. `[data-filter='overdue'], .filter-overdue, button.overdue`) to handle UI variations
