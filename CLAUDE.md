# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Critical: Delegation Policy

**MANDATORY IMMEDIATE DELEGATION ON TOOL BLOCK**

When ANY tool is blocked by the delegation policy hook:

1. **DO NOT try alternative approaches** - just delegate immediately
2. **IMMEDIATELY use `/delegate <task>`** on first tool block
3. **The entire user request must be delegated**, not just the blocked tool

### Recognition Pattern

```
Error: PreToolUse:* hook error: [...] Tool blocked by delegation policy
Tool: <ToolName>

STOP: Do NOT try alternative tools.
REQUIRED: Use /delegate command immediately:
   /delegate <full task description>
```

**Key Points:**
- First tool block = immediate delegation
- Don't explain what you tried - just delegate
- Specialized agents handle execution
- Session registration happens automatically

---

## Prerequisites

- **uv** - Python package manager (required for `uvx`, `uv run`)
- **bun** - JavaScript runtime
- **bc** - Basic calculator (required by statusline)
- **jq** - JSON processor

---

## Build, Lint, and Test Commands

```bash
# Format code (auto-fix)
uvx ruff format .

# Lint code (check only)
uvx ruff check --no-fix .

# Type checking
uvx pyright .

# Dead code detection
uvx deadcode src/

# Run tests
uv run pytest

# Combined pre-commit check (runs all above)
/pre-commit
```

---

## Available Commands

```bash
/delegate <task>           # Route task to specialized agent
/ask <question>            # Read-only question answering
/pre-commit                # Quality checks (Ruff, Pyright, Pytest)
/bypass                    # Toggle delegation enforcement on/off
/add-statusline            # Enable workflow status display
/list-tools                # Show available tools
```

**Skills (auto-invoked by orchestrator):**
- `task-planner` - Explores codebase, decomposes task, returns structured plan (invoked automatically before delegation)

**Multi-step workflows:**
```bash
claude --append-system-prompt "$(cat /system-prompts/workflow_orchestrator.md)" \
  "Your multi-step task"
```

Note: When using the workflow orchestrator system prompt, the `task-planner` skill is automatically invoked BEFORE `/delegate` for every user request.

**In-Session Bypass:**
```bash
/bypass
```

Toggles delegation enforcement on/off from within a Claude Code session. Uses an interactive prompt to let you choose between disabling delegation (bypass hooks) or enabling delegation (enforce hooks). The setting persists until explicitly toggled again.

---

## Architecture Overview

**Hook System:** 6 hook types enforce delegation policy
- **PreToolUse** - Blocks non-allowed tools, enforces allowlist
- **PostToolUse** - Validates Python code (Ruff, Pyright)
- **UserPromptSubmit** - Clears delegation state per user message

**Allowlist:** `AskUserQuestion`, `TodoWrite`, `SlashCommand`, `Task`

**Agent System:** 11 specialized agents matched via keyword detection (>=2 matches)
- Meta: delegation-orchestrator, task-decomposer
- Read-Only: codebase-context-analyzer, code-reviewer
- Implementation: code-cleanup-optimizer, devops-experience-architect
- Verification: task-completion-verifier, phase-validator

**State Files:**
- `.claude/state/delegated_sessions.txt` - Session registry
- `.claude/state/active_delegations.json` - Parallel execution tracking

---

## Agent Selection

Keyword matching algorithm:
1. Extract keywords from task (case-insensitive)
2. Count matches against agent activation keywords
3. Select agent with >=2 matches (highest wins)
4. Fall back to general-purpose if no match

**Examples:**
- "Analyze authentication architecture" -> codebase-context-analyzer
- "Refactor to improve maintainability" -> code-cleanup-optimizer

---

## Python Coding Standards

- Python 3.12+ with modern syntax
- Type hints: `list[str]` not `List[str]`, `str | None` not `Optional[str]`
- No print statements - use logging
- Enforced by: Ruff (linting/formatting), Pyright (type checking)

---

## Debug Commands

```bash
export DEBUG_DELEGATION_HOOK=1        # Enable hook debug logging
tail -f /tmp/delegation_hook_debug.log
export DELEGATION_HOOK_DISABLE=1      # Emergency bypass
cat .claude/state/delegated_sessions.txt  # Check delegation state
```

---

## Troubleshooting

**Tools blocked but delegation fails:**
```bash
ls ~/.claude/hooks/PreToolUse/        # Verify hooks installed
cp -r agents hooks ~/.claude/         # Reinstall if missing
```

**Multi-step not detected:**
Append workflow_orchestrator system prompt and use connectors ("and then", "with", "including").
