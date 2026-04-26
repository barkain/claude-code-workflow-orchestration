# Workflow Orchestrator (Routing Stub)

## Rule

Any user request that requires work — writing code, running tools, multi-step tasks, breadth tasks (same operation across many items), or anything beyond a direct question — **MUST** be handled via:

```
/workflow-orchestrator:delegate <full task description>
```

The main agent does not execute work tools directly. Use only: Tasks API, AskUserQuestion, and `/workflow-orchestrator:delegate`. The delegate command loads the full orchestrator (planning, agent assignment, execution waves) on demand.

## Exception — continuation after plan approval

If you received a "PLAN ALREADY APPROVED" or "continuing to STAGE 1" continuation message from the Stop hook, **do NOT re-invoke `/workflow-orchestrator:delegate`** and **do NOT call `EnterPlanMode`** again. The orchestrator is already loaded and the plan is already approved — proceed directly to Stage 1 execution by rendering the dependency graph and spawning Wave 0 agents. In this exception path, the `Agent` tool (plus `TaskCreate`/`TaskUpdate`/`TaskGet` for status, and `TeamCreate`/`SendMessage` if running in team mode) is permitted — these are how Wave 0 phases are spawned. The "all work → delegate" rule above does NOT apply during in-flight delegation continuation.

**Fallback if plan is missing from context** (e.g., after context-clear): if the continuation message says "PLAN ALREADY APPROVED" but you cannot find the plan in your context:
1. Read `.claude/state/approved_execution_plan.json` to recover the plan, then proceed to Stage 1.
2. If that file is also missing, inform the user the plan was lost and ask them to re-run `/workflow-orchestrator:delegate <original task>`. Do NOT silently re-invoke `/workflow-orchestrator:delegate` yourself.

## What counts as "work"

ANY of these = delegate:
- Reading, searching, editing, or writing files (Read, Grep, Glob, Edit, Write, MultiEdit, NotebookEdit)
- Running shell commands (Bash) for anything beyond a single trivial status check
- Investigating the codebase to answer a question that requires file access → delegate
- Multi-step tasks, even if each step looks simple in isolation

**Exemption:** a single `Read` of an exact file path the user explicitly asked to display (e.g., "show me file X", "read foo.py") may be done directly — no delegation needed.

## What you MUST NOT do

- Do NOT use Read to investigate before deciding — delegate the investigation
- Do NOT run `grep`/`find`/`ls` via Bash — delegate
- Do NOT make "just a small edit" directly — delegate
- Do NOT chain 2+ tool calls to accomplish one user request — delegate

If you catch yourself about to call Bash/Edit/Write/Read/Glob/Grep/MultiEdit/NotebookEdit, STOP and invoke `/workflow-orchestrator:delegate <task>` instead.

## Team Mode

If `TeamCreate` is in your available tools, agent teams are enabled. When you run `/workflow-orchestrator:delegate`, default to team mode (`TeamCreate` + `Agent(team_name=...)`) for multi-agent work. If `TeamCreate` is not available, the delegate flow falls back to parallel subagents automatically.

You do not need to check env vars or run Bash to detect this — tool availability is the signal.

## Pure Q&A

If the user is only asking a question (no work to perform), answer directly.
- Single file the user asked to read → use `Read` directly.
- Multi-file investigation or codebase questions → use `/workflow-orchestrator:delegate <question>`.
