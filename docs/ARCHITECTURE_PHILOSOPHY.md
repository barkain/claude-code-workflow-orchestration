# Architecture Philosophy: Capability Through Constraint

> Comprehensive documentation of the Claude Code Workflow Orchestration System's architectural design, behavioral model, and emergent properties.

---

## Table of Contents

1. [Section 1: Architectural Philosophy](#section-1-architectural-philosophy)
2. [Section 2: The Three Pillars](#section-2-the-three-pillars)
3. [Section 3: Hook System Behavior](#section-3-hook-system-behavior)
4. [Section 4: Agent Orchestration Behavior](#section-4-agent-orchestration-behavior)
5. [Section 5: State Management](#section-5-state-management)
6. [Section 6: Emergent Properties](#section-6-emergent-properties)

---

## Section 1: Architectural Philosophy

### 1.1 The Paradox of Constraint

The Claude Code Workflow Orchestration System embodies a counterintuitive principle: **capability emerges from constraint**. By deliberately restricting what the main Claude agent can do directly, we create a system that achieves more than an unconstrained agent ever could.

```
Traditional Model:  Agent -> [All Tools] -> Results
                    (Unfocused, shallow execution)

Constrained Model:  Agent -> [Delegation] -> [Specialized Agents] -> [Deep Execution] -> Results
                    (Focused, deep execution with verification)
```

### 1.2 Why Constraints Enable Better Outcomes

**Depth Over Breadth**

When an agent has unlimited tool access, it tends toward shallow, immediate solutions. The constraint of delegation forces:
- Task decomposition before execution
- Explicit planning through Tasks API
- Verification at the end of workflows
- Context preservation between phases

**Specialization Through Restriction**

Each specialized agent has a restricted tool set that matches its domain:

| Agent Type | Tool Access | Why |
|------------|-------------|-----|
| Read-Only (analyzer, reviewer) | Read, Glob, Grep, Bash | Objectivity requires inability to modify |
| Implementation (optimizer, devops) | Read, Write, Edit, Glob, Grep, Bash | Can modify but cannot spawn sub-delegations |
| Meta-Agents (orchestrator, decomposer) | Read, Task, Tasks API | Coordinates but doesn't execute directly |
| Verification (verifier, validator) | Read, Bash, Glob, Grep | Validates without modifying (maintains objectivity) |
| Planning (task-planner) | Read, Glob, Grep, Bash, WebFetch, AskUserQuestion | Analyzes and plans but never implements |

### 1.3 Core Design Principles

**Principle 1: More Tasks, Fewer Waves**
- Maximize parallelism by grouping independent tasks into the same wave
- Target: 4+ tasks per wave, 5-6 waves maximum
- Verification as a single wave at the end, not after every implementation

**Principle 2: Parallelism-First**
- Default to parallel execution when tasks are independent
- Sequential execution only when explicit dependencies exist
- Wave synchronization handles dependencies automatically

**Principle 3: Verification at End**
- Single verification wave after all implementation waves complete
- Avoids overhead of verify-after-every-task pattern
- Reduces total workflow execution time

**Principle 4: Conservative Defaults**
- Sequential execution when dependencies unclear (safety fallback)
- When in doubt, decompose further
- Explicit over implicit in all delegation decisions

### 1.4 Architectural Boundaries

```
+-------------------------------------------------------------------+
|                    USER PROMPT BOUNDARY                            |
|  (Delegation state cleared, fresh session for each prompt)         |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    MAIN CLAUDE SESSION                             |
|  Allowlist: Tasks API, AskUserQuestion, SlashCommand, Task         |
|  All other tools: BLOCKED                                          |
+-------------------------------------------------------------------+
                              |
                        /delegate
                              |
+-------------------------------------------------------------------+
|                    DELEGATION BOUNDARY                             |
|  Session registered -> Tool access granted                         |
|  Specialized agent spawned via Task tool                           |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    SPECIALIZED AGENT                               |
|  Tools restricted to agent's declared capabilities                 |
|  Cannot spawn nested delegations (prevents recursion)              |
+-------------------------------------------------------------------+
```

---

## Section 2: The Three Pillars

### 2.1 Pillar One: Context Isolation

**Definition**

Context Isolation ensures that each component operates with only the information and capabilities it needs, preventing unintended state leakage.

**Isolation Mechanisms**

- **Session Isolation**: State cleared between user prompts via UserPromptSubmit hook
- **Agent Isolation**: Each specialized agent runs in its own subagent context
- **State Isolation**: No global mutable state persists across user prompts

**Context Passing Protocol**

```
Phase N Completion
        |
+---------------------------------------+
|         Context Capture               |
|  - File paths (absolute only)         |
|  - Key decisions made                 |
|  - Issues encountered                 |
+---------------------------------------+
        |
Tasks API Update (Phase N -> completed)
        |
Phase N+1 Delegation with captured context
```

### 2.2 Pillar Two: Workflow Governance

**Wave Scheduling**

Tasks are organized into waves for parallel execution:

```
Wave 0 (Parallel): [Task A, Task B, Task C, Task D]
        |
    [Wave Sync: All Wave 0 tasks complete]
        |
Wave 1 (Parallel): [Task E, Task F, Task G]
        |
    [Wave Sync: All Wave 1 tasks complete]
        |
Wave 2 (Final): [Verification]
```

**Wave Validation Rules:**
1. Implementation and verification should be in separate waves
2. No task can depend on another task within the same parallel wave
3. Tasks modifying the same file cannot be in the same parallel wave

**Core Principle: More Tasks, Fewer Waves**
- Target: 4+ tasks per wave
- Maximum: 5-6 waves for typical projects
- If a wave has only 1 task, consider merging with adjacent wave

### 2.3 Pillar Three: Quality Gates

**PreToolUse Gate:**
- Task graph compliance check
- Delegation allowlist enforcement
- Session registration validation

**PostToolUse Gate (Python):**
- Ruff syntax and security validation
- Pyright type checking

**PostToolUse Gate (Task):**
- Task graph depth enforcement
- Tasks API update reminder

---

## Section 3: Hook System Behavior

### 3.1 The Hook Architecture

The system implements hooks across 6 lifecycle events:

```
+-------------------------------------------------------------------+
|                      SESSION LIFECYCLE                             |
+-------------------------------------------------------------------+

1. SessionStart
   - Trigger: Session begins (startup, resume, clear, compact)
   - Hooks: inject-output-style.sh, inject_workflow_orchestrator.sh
   - Output: Session initialized with workflow orchestrator

2. UserPromptSubmit
   - Trigger: Before each user message
   - Hooks: clear-delegation-sessions.sh
   - Output: Fresh session state (no privilege persistence)

3. PreToolUse (matcher: *)
   - Trigger: Before EVERY tool invocation
   - Hooks:
     - validate_task_graph_compliance.sh - Check phase ordering
     - require_delegation.sh - Enforce allowlist, register sessions
   - Output: Allow or block tool execution

4. PostToolUse
   - Matcher: Edit|Write|MultiEdit
     - python_posttooluse_hook.sh - Validate Python code
   - Matcher: Task
     - validate_task_graph_depth.sh - Enforce decomposition depth
     - remind_todo_after_task.sh - Prompt Tasks API update
   - Output: Validated code, task completion reminders

5. SubagentStop
   - Trigger: When subagent completes
   - Hooks:
     - remind_todo_update.sh - Prompt task list update
     - trigger_verification.sh - Trigger verification phase
     - clear-delegation-sessions.sh - Clean up subagent session
   - Output: Wave synchronization, verification triggers

6. Stop
   - Trigger: Session ends
   - Hooks: python_stop_hook.sh - Cleanup stale sessions
   - Output: Clean state for next session
```

### 3.2 Hook Execution Order

PreToolUse hooks execute in registration order:
1. validate_task_graph_compliance.sh (timeout: 5s)
2. require_delegation.sh (timeout: 5s)

First hook failure blocks subsequent hooks and tool execution.

### 3.3 Hook Communication

**Environment Variables:**
- `CLAUDE_SESSION_ID` - Current session identifier
- `CLAUDE_TOOL_NAME` - Tool being invoked
- `CLAUDE_TOOL_ARGUMENTS` - JSON arguments to tool
- `CLAUDE_PARENT_SESSION_ID` - Parent session (for subagents)
- `CLAUDE_PROJECT_DIR` - Project directory override

**State Files:**
- `.claude/state/delegated_sessions.txt` - Session registry
- `.claude/state/active_delegations.json` - Workflow execution state
- `.claude/state/active_task_graph.json` - Current execution plan

**Exit Codes:**
- `0` - Success (allow operation)
- `1` - Failure (block operation)
- `2` - Skip (proceed without processing)

### 3.4 Hook Debugging

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Watch debug log
tail -f /tmp/delegation_hook_debug.log
```

---

## Section 4: Agent Orchestration Behavior

### 4.1 Planning and Orchestration Flow

The system uses a planning-first approach:

```
+-------------------------------------------------------------------+
|                    STAGE 0: PLANNING                               |
|                    (task-planner skill)                            |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
| task-planner (invoked first for complex tasks)                     |
|                                                                    |
| Inputs:                                                            |
| - User request                                                     |
| - Codebase exploration (read-only)                                 |
|                                                                    |
| Processing:                                                        |
| 1. Parse intent and success criteria                               |
| 2. Check for ambiguities (ask if blocking)                         |
| 3. Explore codebase (sample, don't consume)                        |
| 4. Decompose into atomic subtasks                                  |
| 5. Map dependencies                                                |
| 6. Build parallelization plan (more tasks, fewer waves)            |
| 7. Flag risks                                                      |
|                                                                    |
| Output: Structured execution plan                                  |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    STAGE 1: ORCHESTRATION                          |
|                    (delegation-orchestrator)                       |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
| delegation-orchestrator                                            |
|                                                                    |
| Inputs:                                                            |
| - Execution plan from task-planner                                 |
| - Available agent configurations                                   |
|                                                                    |
| Processing:                                                        |
| 1. Agent selection (keyword matching >= 2)                         |
| 2. Wave scheduling                                                 |
| 3. Context template construction                                   |
|                                                                    |
| Output: Agent assignments, delegation prompts                      |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    STAGE 2: EXECUTION                              |
+-------------------------------------------------------------------+
                              |
| Main Claude (with workflow_orchestrator system prompt)             |
|                                                                    |
| Processing:                                                        |
| 1. Create Tasks API task list                                      |
| 2. Execute Wave N phases (spawn via Task)                          |
| 3. Wait for wave sync                                              |
| 4. Capture context from completed phases                           |
| 5. Execute Wave N+1 with context                                   |
| 6. Final verification wave                                         |
| 7. Provide summary                                                 |
+-------------------------------------------------------------------+
```

### 4.2 Agent Selection Algorithm

```python
# Step 1: Extract keywords
task_keywords = set(task.lower().split())
task_keywords -= {"the", "a", "an", "to", "for", "with", "and", "or"}

# Step 2: Count matches
for agent in available_agents:
    matches = len(task_keywords & set(agent.activation_keywords))
    agent.match_count = matches

# Step 3: Apply threshold
candidates = [a for a in agents if a.match_count >= 2]
if not candidates:
    return "general-purpose"
return max(candidates, key=lambda a: a.match_count)
```

### 4.3 Available Agents Reference

| Agent | Keywords | Tool Access | Use Case |
|-------|----------|-------------|----------|
| delegation-orchestrator | delegate, orchestrate, route task | Tasks API, AskUserQuestion | Meta-agent for routing |
| codebase-context-analyzer | analyze, understand, explore, architecture | Read, Glob, Grep, Bash | Code exploration |
| tech-lead-architect | design, approach, research, best practices | Read, Write, Edit, Glob, Grep, Bash | Solution design |
| task-completion-verifier | verify, validate, test, check, review | Read, Bash, Glob, Grep | QA and validation |
| code-cleanup-optimizer | refactor, cleanup, optimize, improve | Read, Write, Edit, Glob, Grep, Bash | Code improvement |
| code-reviewer | review, critique, feedback, assess | Read, Glob, Grep, Bash | Code review |
| devops-experience-architect | setup, deploy, docker, CI/CD | Read, Write, Edit, Glob, Grep, Bash | Infrastructure |
| documentation-expert | document, write docs, README, explain | Read, Write, Edit, Glob, Grep, Bash | Documentation |
| dependency-manager | dependencies, packages, requirements | Read, Write, Edit, Bash | Package management |

### 4.4 Execution Mode Selection

**Parallel Execution (Default for Independent Tasks):**
- Phases operate on different files/systems
- No data dependencies between phases
- Resource isolation (no file conflicts)
- Time benefit expected

**Sequential Execution (When Dependencies Exist):**
- Phase B reads files created by Phase A
- Both phases modify the same file
- Both phases affect the same system state
- Dependencies unclear (conservative fallback)

---

## Section 5: State Management

### 5.1 State File Architecture

```
.claude/
  state/
    delegated_sessions.txt     # Session registry
    active_delegations.json    # Parallel execution tracking
    active_task_graph.json     # Current execution plan
```

### 5.2 Session Registry

**File:** `.claude/state/delegated_sessions.txt`

**Format:** One session ID per line
```
sess_abc123
sess_def456
```

**Lifecycle:**
1. Created when first `/delegate` triggers session registration
2. Populated with session IDs on each delegation
3. Cleared by UserPromptSubmit hook before each user prompt
4. Cleaned of stale sessions (>1 hour) by Stop hook

### 5.3 Active Delegations JSON

**File:** `.claude/state/active_delegations.json`

```json
{
  "version": "2.0",
  "workflow_id": "wf_20250111_143022",
  "execution_mode": "parallel",
  "active_delegations": [
    {
      "delegation_id": "deleg_001",
      "phase_id": "phase_0_0",
      "wave": 0,
      "status": "active",
      "agent": "code-cleanup-optimizer"
    }
  ],
  "max_concurrent": 8
}
```

**Configuration:** Set `CLAUDE_MAX_CONCURRENT` environment variable to override default (e.g., `export CLAUDE_MAX_CONCURRENT=4`).

**Status Values:** `active`, `completed`, `failed`

### 5.4 State Machine

```
                    USER PROMPT
                         |
              +----------------------+
              |  UserPromptSubmit    |
              |  Hook: Clear State   |
              +----------------------+
                         |
                  Attempt Tool
                         |
              +----------------------+
              |  PreToolUse Hook     |
              +----------------------+
                         |
           +-------------+-------------+
           |                           |
    Session in registry?         Tool in allowlist?
           |                           |
       YES: ALLOW               Task/SlashCommand: Register + ALLOW
       NO: Check allowlist      Tasks API/AskUserQuestion: ALLOW
                                Other: BLOCK
```

---

## Section 6: Emergent Properties

### 6.1 Self-Organizing Workflow

**Automatic Verification Injection**

Every workflow concludes with a verification wave:

```
User: "Create calculator.py with tests"
    |
System decomposes to:
    Wave 0: [create add(), create subtract(), create multiply()]
    Wave 1: [create test_add(), create test_subtract(), create test_multiply()]
    Wave 2: [verify all implementations]
```

**Wave-Based Concurrency Control**

The wave system automatically manages concurrency:

```
Wave 0: [Task A, Task B, Task C, Task D] <- All start concurrently
         | (Wave sync: Wait for all)
Wave 1: [Task E, Task F]                 <- Start after Wave 0
         | (Wave sync: Wait for all)
Wave 2: [Verification]                   <- Final verification
```

### 6.2 Fail-Safe Behaviors

**Privilege Decay**

Delegation privileges automatically decay:
1. Session Clearing: UserPromptSubmit clears all sessions
2. Stale Cleanup: Stop hook removes sessions > 1 hour old
3. Subagent Cleanup: SubagentStop clears subagent sessions

**Conservative Defaults**

| Decision Point | Conservative Default |
|----------------|---------------------|
| Execution mode unclear | Sequential |
| Atomicity uncertain | Non-atomic (decompose further) |
| Dependency analysis incomplete | Add dependency |

### 6.3 Observability

**StatusLine (Real-time)**
```
[PAR] Active: 2 Wave 1 | Last: codebase-context-analyzer completed (87s)
```

**Tasks API (Progress Tracking)**
```json
{
  "todos": [
    {"content": "Create calculator.py", "status": "completed"},
    {"content": "Verify implementations", "status": "in_progress"}
  ]
}
```

**Debug Logging**
```
[14:30:22] SESSION=sess_abc TOOL=Read STATUS=blocked REASON=not_delegated
[14:30:23] SESSION=sess_abc TOOL=SlashCommand STATUS=allowed REASON=allowlist
```

### 6.4 Resilience Properties

- **Idempotency**: State operations are safe to repeat
- **Crash Recovery**: State files persist, stale sessions cleaned automatically
- **Partial Failure**: Successful phases preserved, failed phases can retry independently

---

## Appendix A: Architectural Diagram

```
+-------------------------------------------------------------------------+
|                           WORKFLOW ORCHESTRATION SYSTEM                  |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                              USER INTERFACE                              |
|  Commands: /delegate, /ask, /bypass, /add-statusline                    |
|  Skills: task-planner                                                   |
|  StatusLine: [MODE] Active: N Wave W | Last: Event                      |
+-------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|                              HOOK SYSTEM                                 |
|  +----------------+ +------------------+ +-------------+ +-----------+  |
|  | SessionStart   | | UserPromptSubmit | | PreToolUse  | |PostToolUse|  |
|  | inject         | | clear state      | | validate    | | validate  |  |
|  | orchestrator   | | fresh session    | | allowlist   | | python    |  |
|  +----------------+ +------------------+ +-------------+ +-----------+  |
|  +----------------+ +------------------+                                 |
|  | SubagentStop   | |      Stop        |                                 |
|  | wave sync      | | cleanup stale    |                                 |
|  +----------------+ +------------------+                                 |
+-------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|                           ORCHESTRATION LAYER                            |
|  +-------------------------------------------------------------------+  |
|  |                    task-planner (skill)                           |  |
|  |  Intent Parsing -> Codebase Exploration -> Wave Planning          |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    delegation-orchestrator                        |  |
|  |  Agent Selection -> Wave Scheduling -> Context Templates          |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    workflow_orchestrator (system prompt)          |  |
|  |  Task List -> Phase Delegation -> Context Passing -> Verification |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|                           SPECIALIZED AGENTS                             |
|  +-----------------+ +-----------------+ +-----------------+            |
|  | codebase-       | | tech-lead-      | | code-cleanup-   |            |
|  | context-        | | architect       | | optimizer       |            |
|  | analyzer        | | (design)        | | (implement)     |            |
|  | (read-only)     | |                 | |                 |            |
|  +-----------------+ +-----------------+ +-----------------+            |
|  +-----------------+ +-----------------+ +-----------------+            |
|  | task-           | | devops-         | | documentation-  |            |
|  | completion-     | | experience-     | | expert          |            |
|  | verifier        | | architect       | | (docs)          |            |
|  | (validate)      | | (deploy)        | |                 |            |
|  +-----------------+ +-----------------+ +-----------------+            |
+-------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|                              STATE LAYER                                 |
|  .claude/state/                                                          |
|    delegated_sessions.txt    (session registry)                         |
|    active_delegations.json   (parallel execution)                       |
|    active_task_graph.json    (execution plan)                           |
+-------------------------------------------------------------------------+
```

---

## Related Documentation

- [Quick Reference Guide](./ARCHITECTURE_QUICK_REFERENCE.md) - Decision trees and checklists
- [Hook Debugging Guide](./hook-debugging.md) - Detailed hook troubleshooting
- [Environment Variables](./environment-variables.md) - Configuration options
- [StatusLine System](./statusline-system.md) - Real-time status display
- [Python Coding Standards](./python-coding-standards.md) - Code quality requirements
- [Main Documentation](../CLAUDE.md) - Project overview and usage
