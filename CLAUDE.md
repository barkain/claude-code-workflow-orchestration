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
- **bun** - JavaScript runtime (for ccusage cost tracking)
- **jq** - JSON processor (optional, for advanced features)

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
```

---

## Available Commands

```bash
/delegate <task>           # Plan and execute task via task-planner
/ask <question>            # Read-only question answering
/bypass                    # Toggle delegation enforcement on/off
/add-statusline            # Enable workflow status display
```

**Unified Planning:**
The `task-planner` skill is automatically invoked before every delegation. It handles all planning duties:
- Codebase exploration and context gathering
- Task analysis and complexity assessment
- Decomposition into atomic subtasks
- Agent selection via keyword matching (>=2 matches threshold)
- Dependency mapping between subtasks
- Wave assignment for parallel/sequential execution
- TodoWrite population with encoded metadata (execution plan embedded in task entries)

**Note:** The `task-planner` skill now provides unified orchestration. The separate `delegation-orchestrator` agent has been deprecated.

**In-Session Bypass:**
```bash
/bypass
```

Toggles delegation enforcement on/off from within a Claude Code session. Uses an interactive prompt to let you choose between disabling delegation (bypass hooks) or enabling delegation (enforce hooks). The setting persists until explicitly toggled again.

---

## Architecture Overview

**Unified Execution Flow:**
```
User request → task-planner (unified analysis + planning) → Execute phases → Results
```

The `task-planner` skill performs all planning responsibilities:
- Explores codebase and understands context
- Analyzes task complexity and intent
- Decomposes into atomic subtasks with clear boundaries
- Assigns each subtask to a specialized agent via keyword matching
- Maps dependencies between subtasks
- Schedules subtasks into optimal parallel/sequential waves
- Populates TodoWrite with encoded metadata (format: `[W<wave>][<phase_id>][<agent>] <description>`)

**Hook System** (3 active hooks enforce delegation policy):
- **PreToolUse** - Blocks non-allowed tools, enforces allowlist (Read, Glob, Grep blocked)
- **PostToolUse** - Validates Python code (Ruff, Pyright)
- **UserPromptSubmit** - Clears delegation state per user message

**Allowlist:** `AskUserQuestion`, `TodoWrite`, `SlashCommand`, `Task`

**Specialized Agents (8 active):**
- **Analysis & Review:** codebase-context-analyzer, code-reviewer
- **Implementation:** code-cleanup-optimizer, devops-experience-architect
- **Verification:** task-completion-verifier
- **Design:** tech-lead-architect
- **Documentation:** documentation-expert
- **Dependencies:** dependency-manager

**Execution Model:**
- Single-step tasks: Direct agent execution
- Multi-step tasks: Wave-based execution (sequential or parallel)
- Phase dependencies: Automatically detected and optimized
- Context passing: Between phases in sequential workflows
- Progress tracking: TodoWrite updated after each phase/wave

**State Files:**
- `.claude/state/delegated_sessions.txt` - Session registry for delegation enforcement
- `.claude/state/active_delegations.json` - Parallel wave tracking

---

## Agent Selection

The `task-planner` skill uses keyword matching to intelligently assign agents to each subtask:

**Algorithm:**
1. Extract keywords from subtask description (case-insensitive, tokenized)
2. Count keyword matches against each agent's activation keywords
3. Select agent with >=2 matches (highest count wins)
4. Fall back to general-purpose execution if no strong match (0-1 matches)

**Agent Activation Keywords:**
- **codebase-context-analyzer:** analyze, understand, explore, architecture, patterns, structure, dependencies
- **code-reviewer:** review, code review, critique, feedback, assess, evaluate
- **code-cleanup-optimizer:** refactor, cleanup, optimize, improve, technical debt, maintainability
- **devops-experience-architect:** setup, deploy, docker, CI/CD, infrastructure, pipeline, configuration
- **task-completion-verifier:** verify, validate, test, check, review, quality, edge cases
- **tech-lead-architect:** design, approach, research, evaluate, best practices, architect, scalability
- **documentation-expert:** document, write docs, README, explain, create guide, documentation
- **dependency-manager:** dependencies, packages, requirements, install, upgrade, manage

**Examples:**
- "Analyze authentication system architecture" -> codebase-context-analyzer (matches: analyze, architecture)
- "Refactor code to improve maintainability" -> code-cleanup-optimizer (matches: refactor, improve, maintainability)
- "Test and verify functionality" -> task-completion-verifier (matches: test, verify)
- "Setup CI/CD pipeline" -> devops-experience-architect (matches: setup, CI/CD, pipeline)

**Note:** In plugin mode, agent names use the prefix `workflow-orchestrator:` (e.g., `workflow-orchestrator:task-completion-verifier`).

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
