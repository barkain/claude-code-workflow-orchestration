# Documentation Index

> Navigation guide for the Claude Code Workflow Orchestration System documentation.

---

## Quick Start

New to the system? Start here:

1. **[Main Documentation](../CLAUDE.md)** - Project overview, commands, and quick setup
2. **[Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md)** - Decision trees and checklists
3. **[Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md)** - Deep dive into system design

---

## Documentation Map

```
docs/
├── README.md                           (this file - navigation index)
├── ARCHITECTURE_PHILOSOPHY.md          (comprehensive design documentation)
├── ARCHITECTURE_QUICK_REFERENCE.md     (decision trees, checklists)
├── hook-debugging.md                   (hook troubleshooting guide)
├── environment-variables.md            (configuration options)
├── statusline-system.md                (real-time status display)
├── python-coding-standards.md          (code quality requirements)
├── validation-schema.md                (JSON schema validation)
├── semantic_validation.md              (semantic task validation)
├── pain-points-solutions-report.md     (known issues and solutions)
└── design/
    └── workflow_state_system.md        (state management design)
```

---

## Documentation by Topic

### Architecture and Design

| Document | Description | Audience |
|----------|-------------|----------|
| [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md) | Core design principles, three pillars, emergent properties | Architects, Contributors |
| [Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md) | Decision trees, agent tables, debugging checklists | All Users |
| [Workflow State System](./design/workflow_state_system.md) | State management design details | Contributors |

### Configuration and Setup

| Document | Description | Audience |
|----------|-------------|----------|
| [Environment Variables](./environment-variables.md) | DEBUG_DELEGATION_HOOK, DELEGATION_HOOK_DISABLE, CLAUDE_PROJECT_DIR | All Users |
| [Main CLAUDE.md](../CLAUDE.md) | Installation, commands, usage | All Users |

### Debugging and Troubleshooting

| Document | Description | Audience |
|----------|-------------|----------|
| [Hook Debugging Guide](./hook-debugging.md) | All 6 hooks, integration testing, common issues | Developers |
| [Pain Points Report](./pain-points-solutions-report.md) | Known issues and solutions | All Users |
| [Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md) | Debugging checklists | All Users |

### System Components

| Document | Description | Audience |
|----------|-------------|----------|
| [StatusLine System](./statusline-system.md) | Real-time workflow status display | All Users |
| [Hook Debugging Guide](./hook-debugging.md) | 6-hook lifecycle documentation | Developers |

### Code Quality

| Document | Description | Audience |
|----------|-------------|----------|
| [Python Coding Standards](./python-coding-standards.md) | Type hints, linting, security rules | Developers |
| [Validation Schema](./validation-schema.md) | JSON schema for state files | Contributors |
| [Semantic Validation](./semantic_validation.md) | Task atomicity and complexity validation | Contributors |

---

## By Use Case

### "I want to understand how the system works"

1. Start with [Main CLAUDE.md](../CLAUDE.md) for overview
2. Read [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md) for design principles
3. Reference [Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md) for practical details

### "Something isn't working"

1. Check [Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md) debugging checklists
2. Use [Hook Debugging Guide](./hook-debugging.md) for hook-specific issues
3. Review [Pain Points Report](./pain-points-solutions-report.md) for known issues

### "I want to configure the system"

1. See [Environment Variables](./environment-variables.md) for all options
2. Check [Main CLAUDE.md](../CLAUDE.md) for settings.json structure

### "I want to contribute to the project"

1. Read [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md) for design understanding
2. Follow [Python Coding Standards](./python-coding-standards.md) for code quality
3. Review [Validation Schema](./validation-schema.md) for state file formats

### "I want to monitor workflow execution"

1. Set up [StatusLine System](./statusline-system.md)
2. Enable debug logging per [Environment Variables](./environment-variables.md)
3. Use debugging commands from [Architecture Quick Reference](./ARCHITECTURE_QUICK_REFERENCE.md)

---

## Quick Links

### Commands

```bash
/delegate <task>           # Route task to specialized agent
/ask <question>            # Read-only question answering
/pre-commit                # Quality checks (Ruff, Pyright, Pytest)
/list-tools                # Show available tools
```

### Debug Commands

```bash
export DEBUG_DELEGATION_HOOK=1           # Enable hook logging
tail -f /tmp/delegation_hook_debug.log   # Watch debug log
cat .claude/state/delegated_sessions.txt # Check delegation state
```

### Emergency Commands

```bash
export DELEGATION_HOOK_DISABLE=1         # Emergency bypass (use sparingly!)
```

---

## Document Conventions

### Symbols Used

| Symbol | Meaning |
|--------|---------|
| Y | Has access / Supported |
| - | No access / Not supported |
| PASS | Validation succeeded |
| FAIL | Validation failed |
| BLOCK | Operation blocked |

### Code Block Types

```bash
# Bash commands (executable)
```

```python
# Python code (reference/pseudocode)
```

```json
# JSON structure (schema/example)
```

```
# Plain text (diagrams, output)
```

---

## Version Information

| Component | Version |
|-----------|---------|
| State Schema | 2.0 |
| Documentation | 2025-01 |
| Minimum Python | 3.12+ |

---

## External Resources

### Claude Code
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)

### Tools
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pyright Documentation](https://microsoft.github.io/pyright/)
- [UV Package Manager](https://docs.astral.sh/uv/)

---

## Feedback and Contributions

Found an issue or want to improve the documentation?

1. Check existing [Pain Points Report](./pain-points-solutions-report.md)
2. File an issue in the repository
3. Submit a pull request with improvements

---

## Document Maintenance

| Document | Last Updated | Status |
|----------|--------------|--------|
| ARCHITECTURE_PHILOSOPHY.md | 2025-01 | Current |
| ARCHITECTURE_QUICK_REFERENCE.md | 2025-01 | Current |
| hook-debugging.md | 2025-01 | Current |
| environment-variables.md | 2025-01 | Current |
| statusline-system.md | 2025-01 | Current |
| python-coding-standards.md | 2025-01 | Current |
| validation-schema.md | 2025-01 | Current |
| semantic_validation.md | 2024-12 | Current |
| pain-points-solutions-report.md | 2025-01 | Current |
| workflow_state_system.md | 2025-01 | Current |
