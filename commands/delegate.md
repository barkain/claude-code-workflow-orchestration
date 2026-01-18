---
description: Execute task-planner output by delegating phases to specialized agents
argument-hint: [task description]
allowed-tools: Task
---

# Task Execution

**USER TASK:** $ARGUMENTS

---

## Process Overview

This command executes the unified plan created by the `task-planner` skill. Task-planner is a unified planning orchestrator that:
- Analyzes the user's request and intent
- Explores the codebase to understand context
- Decomposes the task into atomic subtasks
- Assigns specialized agents to each subtask via keyword matching (>=2 match threshold)
- Maps dependencies between subtasks
- Assigns subtasks to parallel/sequential waves (maximizing parallelism)
- Populates TodoWrite with encoded task metadata
- Generates the JSON execution plan (the binding contract)

**Your role: Execute the plan exactly as specified. Never deviate from wave order, phase assignments, or dependencies.**

---

## Step 1: Invoke Task Planner

Invoke the `task-planner` skill to perform unified task analysis, planning, and scheduling:

```
/task-planner $ARGUMENTS
```

Task-planner handles ALL planning responsibilities:
- **Analysis**: Parses intent, checks for ambiguities, explores codebase
- **Decomposition**: Breaks task into atomic subtasks with clear boundaries
- **Agent Assignment**: Matches each subtask to a specialized agent using keyword matching
- **Dependency Mapping**: Analyzes what blocks what and what can parallelize
- **Wave Scheduling**: Groups independent subtasks into parallel waves (minimizing total waves)
- **Progress Tracking**: Populates TodoWrite with encoded metadata
- **Execution Plan**: Returns JSON execution plan as the binding contract

The output includes:
- Subtask table with agent assignments and dependencies
- Wave breakdown (each task listed individually)
- JSON execution plan (use this as your binding contract)
- TodoWrite entries (auto-populated for tracking)

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

**Update TodoWrite after each phase:**
- Mark completed phases as `completed`
- Mark current phase as `in_progress`
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

1. Invoke `/task-planner $ARGUMENTS`
2. Parse the execution plan JSON
3. Execute waves in order
4. Report results

Trust the task-planner. Execute the plan exactly as specified.
