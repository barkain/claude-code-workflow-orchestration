# Workflow Orchestrator (Routing Stub)

## Rule

Any user request that requires work — writing code, running tools, multi-step tasks, breadth tasks (same operation across many items), or anything beyond a direct question — **MUST** be handled via:

```
/workflow-orchestrator:delegate <full task description>
```

The main agent does not execute work tools directly. Use only: Tasks API, AskUserQuestion, and `/workflow-orchestrator:delegate`. The delegate command loads the full orchestrator (planning, agent assignment, execution waves) on demand.

## Team Mode

If `TeamCreate` is in your available tools, agent teams are enabled. When you run `/workflow-orchestrator:delegate`, default to team mode (`TeamCreate` + `Agent(team_name=...)`) for multi-agent work. If `TeamCreate` is not available, the delegate flow falls back to parallel subagents automatically.

You do not need to check env vars or run Bash to detect this — tool availability is the signal.

## Pure Q&A

If the user is only asking a question (no work to perform), answer directly. Use `/workflow-orchestrator:ask <question>` for read-only investigation that needs file access.
