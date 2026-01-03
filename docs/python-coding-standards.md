# Python Coding Standards

> Reference documentation for the Claude Code Delegation System.
> Main documentation: [CLAUDE.md](../CLAUDE.md)

---

## Table of Contents

- [Python Version](#python-version)
- [Type Annotations](#type-annotations)
- [Logging Standards](#logging-standards)
- [Code Quality Standards](#code-quality-standards)
- [Security Standards](#security-standards)
- [Performance Standards](#performance-standards)
- [Hook Enforcement](#hook-enforcement)
- [Running Validation Manually](#running-validation-manually)

---

## Python Version

**Required:** Python 3.12+

All code in this project must use modern Python 3.12+ syntax and features. This enables:

- Native type parameter syntax (`class Box[T]: ...`)
- Improved error messages
- Performance improvements
- Latest standard library features

---

## Type Annotations

### Modern Type Hint Syntax (Required)

Use Python 3.10+ union syntax and built-in generics. Do NOT use deprecated `typing` module imports.

**Correct:**

```python
def process(items: list[str]) -> dict[str, int]:
    """Process items and return counts."""
    return {item: len(item) for item in items}

def get_value(key: str) -> str | None:
    """Get value or None if not found."""
    return data.get(key)

def combine(a: int | float, b: int | float) -> int | float:
    """Add two numbers."""
    return a + b
```

**Incorrect:**

```python
from typing import List, Dict, Optional, Union

def process(items: List[str]) -> Dict[str, int]:  # Don't use typing.List
    return {item: len(item) for item in items}

def get_value(key: str) -> Optional[str]:  # Use str | None instead
    return data.get(key)

def combine(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    return a + b
```

### Enforced Ruff Rules

| Rule | Description | Example |
|------|-------------|---------|
| **UP006** | Use `list[T]` instead of `List[T]` | `list[str]` not `List[str]` |
| **UP007** | Use `X \| Y` instead of `Union[X, Y]` or `Optional[X]` | `str \| None` not `Optional[str]` |
| **UP035** | Import replacements for deprecated typing features | Use built-in types |
| **UP037** | Remove quotes from type annotations | Use `from __future__ import annotations` if needed |

### Type Hint Best Practices

```python
# Collections - use built-in types
items: list[str] = []
mapping: dict[str, int] = {}
unique: set[int] = set()
coordinates: tuple[float, float] = (0.0, 0.0)

# Optional values - use union with None
name: str | None = None

# Multiple types - use union
value: int | float | str = 0

# Callable types
from collections.abc import Callable
handler: Callable[[str, int], bool] = my_function

# Iterables
from collections.abc import Iterable, Iterator
def process(items: Iterable[str]) -> Iterator[str]:
    for item in items:
        yield item.upper()
```

---

## Logging Standards

### No Print Statements in Production Code

Use the `logging` module for all output. Print statements are blocked by Ruff rule T201.

**Correct:**

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: dict) -> None:
    logger.info("Processing data with %d items", len(data))
    logger.debug("Data contents: %s", data)

    try:
        result = transform(data)
        logger.info("Successfully processed data")
    except ValueError as e:
        logger.error("Failed to process data", exc_info=True)
        raise
```

**Incorrect:**

```python
def process_data(data: dict) -> None:
    print(f"Processing data with {len(data)} items")  # Blocked by T201
    print(f"Data: {data}")  # Blocked by T201
```

### Exceptions to Print Rule

Print statements are allowed in:

- Test files (`test_*.py`, `**/tests/**/*.py`)
- CLI entry points (`cli.py`, `main.py`, `__main__.py`)
- Scripts intended for direct execution

### Logging Best Practices

```python
import logging

# Configure at module level
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed diagnostic information")
logger.info("General informational messages")
logger.warning("Warning about potential issues")
logger.error("Error that doesn't stop execution", exc_info=True)
logger.critical("Critical error that may stop execution")

# Use lazy formatting (not f-strings in log calls)
logger.info("Processing %s with %d items", name, count)  # Correct
logger.info(f"Processing {name} with {count} items")     # Less efficient
```

---

## Code Quality Standards

### Import Management

| Rule | Description |
|------|-------------|
| **F401** | Remove unused imports |
| **F811** | No redefined imports |
| **I001** | Sort imports (use `isort` or `ruff format`) |

**Correct import order:**

```python
# Standard library
import logging
import os
from pathlib import Path

# Third-party
import requests
from pydantic import BaseModel

# Local
from .utils import helper
from .models import User
```

### Error Handling

| Rule | Description |
|------|-------------|
| **BLE001** | Don't use bare `except Exception:` |
| **TRY002** | Use `raise ... from ...` to preserve context |
| **TRY400** | Include `exc_info=True` when logging errors |

**Correct:**

```python
try:
    result = dangerous_operation()
except ValueError as e:
    logger.error("Operation failed", exc_info=True)
    raise ProcessingError("Failed to process") from e
except KeyError as e:
    logger.warning("Key not found: %s", e)
    return default_value
```

**Incorrect:**

```python
try:
    result = dangerous_operation()
except Exception:  # Too broad - BLE001
    logger.error("Operation failed")  # Missing exc_info - TRY400
    raise ProcessingError("Failed")  # Missing 'from e' - TRY002
```

---

## Security Standards

### Critical Security Violations (Blocking)

The following patterns are **blocked** by the PostToolUse hook and will prevent code from being saved:

| Rule | Pattern | Risk |
|------|---------|------|
| **S102** | `exec()` usage | Arbitrary code execution |
| **S307** | `eval()` usage | Arbitrary code execution |
| **S105-S107** | Hardcoded passwords/secrets | Credential exposure |
| **S301-S302** | `pickle`/`marshal` usage | Unsafe deserialization |
| **S311** | `random` for security | Predictable values |
| **S501** | `verify=False` in requests | Insecure TLS |
| **S506** | `yaml.load()` without Loader | Arbitrary code execution |

### Secure Random Values

**Correct:**

```python
import secrets

# Generate secure random token
token = secrets.token_urlsafe(32)

# Generate secure random bytes
key = secrets.token_bytes(32)

# Secure random integer
secure_int = secrets.randbelow(100)
```

**Incorrect:**

```python
import random
import string

# Insecure for security purposes - S311
token = ''.join(random.choices(string.ascii_letters, k=32))
```

### Safe YAML Loading

**Correct:**

```python
import yaml

# Use safe_load for untrusted input
with open("config.yml") as f:
    config = yaml.safe_load(f)

# Or explicitly specify SafeLoader
config = yaml.load(data, Loader=yaml.SafeLoader)
```

**Incorrect:**

```python
import yaml

# Unsafe - allows arbitrary code execution - S506
with open("config.yml") as f:
    config = yaml.load(f)  # Missing Loader argument
```

### SQL Injection Prevention

Never concatenate user input into SQL queries:

**Correct:**

```python
# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# With named parameters
cursor.execute(
    "SELECT * FROM users WHERE name = :name AND age > :age",
    {"name": username, "age": min_age}
)
```

**Incorrect:**

```python
# SQL injection vulnerabilities
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
```

### Command Injection Prevention

Use subprocess with list arguments, never shell=True with user input:

**Correct:**

```python
import subprocess

# List arguments prevent injection
subprocess.run(["git", "commit", "-m", message], check=True)

# Use shlex.quote if shell is absolutely necessary
import shlex
subprocess.run(f"echo {shlex.quote(user_input)}", shell=True)
```

**Incorrect:**

```python
import os
import subprocess

# Command injection vulnerabilities
os.system(f"git commit -m {message}")
subprocess.run(f"git commit -m {message}", shell=True)
subprocess.call("echo " + user_input, shell=True)
```

### Secrets Management

**Correct:**

```python
import os

# Read from environment
api_key = os.environ.get("API_KEY")
database_url = os.environ["DATABASE_URL"]

# Or from secure configuration
from config import get_secret
api_key = get_secret("api_key")
```

**Incorrect:**

```python
# Hardcoded secrets - S105, S106, S107
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"
SECRET_KEY = "my-secret-key"
```

---

## Performance Standards

| Rule | Description |
|------|-------------|
| **PERF102** | Use comprehensions efficiently |
| **PERF401** | Prefer list comprehensions over manual loops |

**Correct:**

```python
# List comprehension
squares = [x**2 for x in range(10)]

# Dict comprehension
word_lengths = {word: len(word) for word in words}

# Generator for large datasets
large_sum = sum(x**2 for x in range(1000000))
```

**Less efficient:**

```python
# Manual loop - PERF401
squares = []
for x in range(10):
    squares.append(x**2)
```

---

## Hook Enforcement

All standards above are enforced by `src/hooks/PostToolUse/python_posttooluse_hook.sh` which runs automatically after every Python file Write/Edit operation.

### Validation Stages

1. **Critical Security Check** (fast pattern matching)
   - `exec()`, `eval()` usage
   - Hardcoded passwords/secrets
   - Unsafe serialization (`pickle`, `marshal`)
   - Insecure random (`random` vs `secrets`)
   - TLS verification disabled
   - Unsafe YAML loading

2. **Ruff Validation** (comprehensive linting)
   - Modern type hints
   - No print statements
   - Import management
   - Error handling best practices
   - Security patterns

3. **Pyright Type Checking** (type safety)
   - Type annotation correctness
   - Type compatibility
   - Missing type hints

### Blocking Behavior

Operations that violate these standards are **blocked** with detailed error messages. The file will not be saved until issues are resolved.

Example error output:

```
PostToolUse validation failed for /path/to/file.py

CRITICAL SECURITY ISSUES:
  S301: Use of pickle.loads() detected - unsafe deserialization

RUFF ERRORS:
  UP006: Use `list` instead of `List` for type annotation
  T201: `print` found - use logging instead

Please fix these issues and try again.
```

---

## Running Validation Manually

Test your code against these standards before committing:

```bash
# Full validation using the hook script
./src/hooks/PostToolUse/python_posttooluse_hook.sh your_file.py

# Run Ruff directly
ruff check your_file.py

# Run Ruff with auto-fix
ruff check --fix your_file.py

# Run Pyright directly
pyright your_file.py

# Format with Ruff
ruff format your_file.py
```

### Skip Specific Checks

For testing or debugging, you can skip specific validation stages:

```bash
# Skip Ruff validation
CHECK_RUFF=0 ./src/hooks/PostToolUse/python_posttooluse_hook.sh your_file.py

# Skip Pyright validation
CHECK_PYRIGHT=0 ./src/hooks/PostToolUse/python_posttooluse_hook.sh your_file.py

# Skip both (only critical security check)
CHECK_RUFF=0 CHECK_PYRIGHT=0 ./src/hooks/PostToolUse/python_posttooluse_hook.sh your_file.py
```

### IDE Integration

For real-time feedback, configure your IDE:

**VS Code:**
- Install "Ruff" extension
- Install "Pylance" extension (uses Pyright)

**PyCharm:**
- Install "Ruff" plugin
- Enable type checking in settings

---

## Quick Reference Card

### Type Hints

| Old Style | New Style |
|-----------|-----------|
| `List[str]` | `list[str]` |
| `Dict[str, int]` | `dict[str, int]` |
| `Set[int]` | `set[int]` |
| `Tuple[int, str]` | `tuple[int, str]` |
| `Optional[str]` | `str \| None` |
| `Union[int, str]` | `int \| str` |

### Security Patterns

| Avoid | Use Instead |
|-------|-------------|
| `exec()` | Specific functions |
| `eval()` | `ast.literal_eval()` or JSON |
| `pickle.loads()` | JSON or safe formats |
| `random.random()` | `secrets.token_*()` |
| `yaml.load()` | `yaml.safe_load()` |
| `verify=False` | Proper TLS certificates |

---

## Related Documentation

- [Hook Debugging Guide](./hook-debugging.md) - PostToolUse hook debugging
- [Environment Variables](./environment-variables.md) - Validation settings
- [Main Documentation](../CLAUDE.md) - Complete system reference
