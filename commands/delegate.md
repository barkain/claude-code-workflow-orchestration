---
description: Intelligently delegate tasks to specialized agents with multi-step detection
argument-hint: [task description]
allowed-tools: Task
---

# Intelligent Task Delegation

**USER TASK:** $ARGUMENTS

---

## Process Overview

This command uses a **two-stage delegation architecture**:

1. **Stage 1: Orchestration** - delegation-orchestrator analyzes task, selects agents, creates execution plan
2. **Stage 2: Execution** - Main agent executes plan exactly as specified

---

## Step 1: Spawn Orchestrator

Spawn `delegation-orchestrator` with the user's complete task. The orchestrator returns:
- Task type (single-step vs multi-step)
- Agent assignments per phase
- JSON execution plan
- TodoWrite entries (already populated)

---

## Step 2: Parse Recommendation

Extract from orchestrator output:

**Single-Step:** Look for agent assignment and task description.

**Multi-Step:** Extract JSON execution plan from code fence. This JSON is a **BINDING CONTRACT**.

---

## Step 3: Execute Plan

**BINDING CONTRACT RULES - NO EXCEPTIONS:**

- Execute waves in order (Wave 0 -> Wave 1 -> ...)
- For parallel waves: spawn ALL phase Tasks in SINGLE message
- For sequential waves: execute one phase at a time
- NEVER simplify, reorder, skip, or modify the plan
- Include phase ID in every Task invocation:
  ```
  Phase ID: [phase_id]
  Agent: [agent-name]
  [Task description]
  ```

**Context Passing Between Phases:**

Capture and pass between phases:
- File paths (absolute paths only)
- Key decisions made
- Configurations determined
- Issues encountered

Prepend context to next phase prompt:
```
CONTEXT FROM PREVIOUS PHASE:
- Created file: /absolute/path/to/file.ext
- Key decisions: [summary]
---
[Phase delegation prompt]
```

---

## Step 4: Report Results

Provide completion summary:
- Phases executed and their agents
- Deliverables with absolute paths
- Key decisions made
- Recommended next steps

---

## Error Handling

- If orchestrator fails: ask user for clarification
- If phase fails: stop workflow, report failure, ask user whether to retry or abort
- If plan seems impractical: use `/ask` to notify user, wait for decision

---

## Begin Delegation

Execute Steps 1-4. Trust the orchestrator. Execute the plan exactly as specified.
