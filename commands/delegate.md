---
description: Execute task-planner output by delegating phases to specialized agents
argument-hint: [task description]
allowed-tools: Task
---

# Task Execution

**USER TASK:** $ARGUMENTS

---

## Process Overview

This command executes the plan that was created by task-planner in Stage 0 (workflow_orchestrator).

**Important:** Task-planner has ALREADY run before this command is invoked. Do NOT invoke task-planner again - the plan already exists in the task list (use TaskList to view) and the execution plan JSON.

**Your role: Execute the plan exactly as specified. Never deviate from wave order, phase assignments, or dependencies.**

---

## Step 1: Use Task-Planner Output from Stage 0

The task-planner skill already ran in Stage 0 and produced:
- Tasks created via TaskCreate with structured metadata (use TaskList to view)
- Subtask table with agent assignments and dependencies
- Wave breakdown (each task listed individually)
- JSON execution plan (your binding contract)

**DO NOT invoke task-planner again.** The planning is complete. Proceed directly to parsing and executing the existing plan.

---

## Step 2: Parse Execution Plan

Extract the JSON execution plan from the task-planner output. This JSON is your **BINDING CONTRACT** and must be followed exactly.

Look for the `Execution Plan JSON` code fence containing:
- `waves[]` - ordered list of execution waves (Wave 0 -> Wave 1 -> ...)
- `phases[]` - individual tasks within each wave with agent assignments
- `dependency_graph` - which phases depend on which other phases
- `parallel_execution` flag - whether phases in a wave run concurrently or sequentially

Task-planner already performed all analysis and optimization. Your job is execution, not re-planning.

---

## Unified Planning Architecture

**OLD approach (deprecated):**
- task-planner (analysis) -> delegation-orchestrator (routing) -> execution

**NEW unified approach (current):**
- task-planner (analysis + decomposition + agent selection + wave scheduling + routing) -> execution

Task-planner now handles everything in one unified pass:
1. Analyzes task complexity and dependencies
2. Assigns agents using keyword matching (>=2 match threshold)
3. Schedules waves for optimal parallel execution
4. Returns the execution plan directly

There is NO separate orchestrator step. Task-planner IS the orchestrator.

---

## Step 3: Execute Plan

**BINDING CONTRACT RULES - NO EXCEPTIONS:**

- Execute waves in order (Wave 0 -> Wave 1 -> ...)
- For parallel waves (`parallel_execution: true`): spawn ALL phase Tasks in SINGLE message
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

**Update task status after each phase:**
- Use TaskUpdate to mark completed phases as `completed`
- Use TaskUpdate to mark current phase as `in_progress`
- Keep pending phases as `pending`

---

## Step 4: Report Results

Provide completion summary:
- Phases executed and their agents
- Deliverables with absolute paths
- Key decisions made
- Recommended next steps

---

## Error Handling

- If task-planner asks for clarification: relay to user, wait for response
- If phase fails: stop workflow, report failure, ask user whether to retry or abort
- If plan seems impractical: use `/ask` to notify user, wait for decision

---

## Begin Execution

1. Locate the execution plan JSON from Stage 0 (already available)
2. Parse the execution plan
3. Execute waves in order
4. Report results

Task-planner already ran in Stage 0. Execute the plan exactly as specified.
