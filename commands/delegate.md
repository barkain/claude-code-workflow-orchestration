---
description: Execute task-planner output by delegating phases to specialized agents
argument-hint: [task description]
allowed-tools: Task
---

# Routing Check (FIRST)

**Step 1: Write Detection** - Check FIRST before breadth routing:

| Write Indicators (case-insensitive) |
|-------------------------------------|
| create, write, save, generate, produce, output, report, build, make |

**If ANY write indicator found:** Skip breadth-reader, proceed to task-planner below.

**Step 2: Breadth Task Detection** - Only if NO write indicators:

| Criteria | Breadth Keywords | Scope Keywords |
|----------|------------------|----------------|
| Single action verb + broad scope | review, explore, summarize, scan, list, catalog, search, find | all files, entire, each, codebase, repository, every |

**If breadth task detected (and no write indicators):** Use `/breadth-reader $ARGUMENTS` instead - STOP HERE.

**Otherwise:** Proceed with task-planner execution below.

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

## Step 3: Execute Plan

**BINDING CONTRACT RULES - NO EXCEPTIONS:**

- Execute waves in order (Wave 0 -> Wave 1 -> ...)
- For parallel waves (`parallel_execution: true`): spawn in batches of **max_concurrent** (from execution plan)
  - **Extract max_concurrent from execution plan JSON** (task-planner reads env var and embeds value)
  - Look for `"max_concurrent": <value>` in the JSON or **Max Concurrent** field in plan header
  - If wave has >max_concurrent phases: spawn first batch, wait for completion, spawn next batch, repeat
  - This prevents context exhaustion while preserving parallelism
  - **DO NOT use Bash** - the main agent cannot run Bash commands (blocked by delegation policy)
- For sequential waves: execute one phase at a time
- NEVER simplify, reorder, skip, or modify the plan

**Agent Prompt Template:** See workflow_orchestrator.md "Agent Prompt Template" section.

**Key points:**
- Extract `output_file` from task metadata (path format: `$CLAUDE_SCRATCHPAD_DIR/{sanitized_subject}.md`)
- Agents write full output to file, return only `DONE|{path}` (nothing else)
- Pass context (file paths, decisions) between phases
- Output files use descriptive names (e.g., `review_auth_module.md`) for easier identification
- The scratchpad directory is automatically session-isolated

**CRITICAL - File Writing:**
- Agents HAVE Write tool access for /tmp/ paths
- Agents write directly to the output_file path - do NOT delegate file writing
- If Write is blocked, report error and stop (do not loop)

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
