---
description: Execute test suite to ensure code changes don't break functionality
argument-hint: [model]
allowed-tools: Task
---

# Run Tests - Execute Test Suite (Delegated)

This command delegates test execution to a general-purpose agent while preserving all test functionality.

## Usage
- `/run-tests` (uses default Sonnet model)
- `/run-tests haiku` (uses Haiku model)
- `/run-tests sonnet` (uses Sonnet model) 
- `/run-tests opus` (uses Opus model)

## Task Delegation

**Arguments:** $ARGUMENTS

You are delegating a test execution task to a general-purpose agent. Parse arguments for optional model preference (default: Sonnet).

**Instructions for Agent:**

Run all tests to ensure code changes don't break existing functionality.

Execute the following commands as appropriate for the project:
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/test_specific.py -v

# Run async tests
uv run pytest --asyncio-mode=auto
```

Make sure all tests pass before committing changes. Provide clear output about test results and any failures that need to be addressed.