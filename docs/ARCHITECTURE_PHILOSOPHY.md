# Architecture Philosophy: Capability Through Constraint

> Comprehensive documentation of the Claude Code Workflow Orchestration System's architectural design, behavioral model, and emergent properties.

---

## Table of Contents

1. [Section 1: Architectural Philosophy](#section-1-architectural-philosophy)
2. [Section 2: The Three Pillars](#section-2-the-three-pillars)
3. [Section 3: Hook System Behavior](#section-3-hook-system-behavior)
4. [Section 4: Agent Orchestration Behavior](#section-4-agent-orchestration-behavior)
5. [Section 5: State Management](#section-5-state-management)
6. [Section 6: Dual-Mode Execution Philosophy](#section-6-dual-mode-execution-philosophy)
7. [Section 7: Emergent Properties](#section-7-emergent-properties)

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
| Planning (native plan mode) | EnterPlanMode, ExitPlanMode, Read, Glob, Grep, Bash | Main agent plans directly via plan mode |

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

**Subagent Mode (Default):**

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
|  Specialized agent spawned via Task tool (isolated)                |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    SPECIALIZED AGENT                               |
|  Tools restricted to agent's declared capabilities                 |
|  Cannot spawn nested delegations (prevents recursion)              |
|  Returns: DONE|{path} (no inter-agent communication)               |
+-------------------------------------------------------------------+
```

**Team Mode (Experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):**

```
+-------------------------------------------------------------------+
|                    USER PROMPT BOUNDARY                            |
|  (Delegation state cleared, team state cleaned up)                 |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    MAIN CLAUDE SESSION (Team Lead)                 |
|  Allowlist: Tasks API, AskUserQuestion, Task, TeamCreate,          |
|             SendMessage, SlashCommand                              |
+-------------------------------------------------------------------+
                              |
                    TeamCreate(team_name="...")
                              |
+-------------------------------------------------------------------+
|                    TEAM BOUNDARY                                    |
|  Task(team_name="...") spawns teammates (shared context)           |
|  Teammates communicate via SendMessage                             |
+-------------------------------------------------------------------+
                         /    |    \
+------------------+ +------------------+ +------------------+
| TEAMMATE A       | | TEAMMATE B       | | TEAMMATE C       |
| [agent config]   | | [agent config]   | | [agent config]   |
| Shared task list | | Shared task list | | Shared task list |
| SendMessage <--> | | SendMessage <--> | | SendMessage <--> |
+------------------+ +------------------+ +------------------+
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

**Context Passing Protocol (Subagent Mode)**

```
Phase N Completion
        |
+---------------------------------------+
|         Minimal Return                |
|  - Agent returns: DONE|{path}         |
|  - Output written to scratchpad       |
|    ($CLAUDE_SCRATCHPAD_DIR)           |
|  - NO TaskOutput polling              |
|  - Wait for completion notification   |
+---------------------------------------+
        |
Tasks API Update (Phase N -> completed)
        |
Phase N+1 reads scratchpad file for context
```

**Context Passing Protocol (Team Mode)**

```
Phase N Completion
        |
+---------------------------------------+
|         Teammate Return               |
|  - Agent writes output to scratchpad  |
|  - Agent messages teammates directly  |
|    via SendMessage (peer-to-peer)     |
|  - Shared task list for coordination  |
|  - Lead receives completion message   |
+---------------------------------------+
        |
Lead syncs: TaskUpdate (Phase N -> completed)
        |
Next wave teammates spawned with context
```

**PROHIBITED Operations (Context Exhaustion Prevention):**
- `TaskOutput` - Causes context window exhaustion
- `TaskList` polling - Use completion notifications instead
- Agents returning full results - Return `DONE|{path}` only

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
     - validate_task_graph_compliance.py - Check phase ordering
       (bypassed when team mode is active)
     - require_delegation.py - Enforce allowlist, register sessions
       (auto-provisions team_mode_active state file when
        CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 and team tool used)
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
- `CLAUDE_TOOL_INPUT` - JSON arguments to tool (preferred)
- `CLAUDE_TOOL_ARGUMENTS` - JSON arguments to tool (legacy)
- `CLAUDE_PARENT_SESSION_ID` - Parent session (subagent detection, hooks skip when set)
- `CLAUDE_PROJECT_DIR` - Project directory override
- `CLAUDE_SCRATCHPAD_DIR` - Agent output directory for scratchpad files
- `CLAUDE_MAX_CONCURRENT` - Max parallel agents per batch (default: 8)

**State Files:**
- `.claude/state/delegated_sessions.txt` - Session registry (legacy)
- `.claude/state/active_delegations.json` - Workflow execution state (includes `delegation_active` flag)
- `.claude/state/active_task_graph.json` - Current execution plan
- `.claude/state/team_mode_active` - Signals hooks that Agent Teams mode is active (team mode only)
- `.claude/state/team_config.json` - Active team configuration: name, teammates, role mappings (team mode only)

**Write Tool Allowed Paths:**
- `/tmp/` - Temporary files
- `/private/tmp/` - macOS private temp
- `/var/folders/` - macOS user temp
- `$CLAUDE_SCRATCHPAD_DIR` - Agent output scratchpad

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

### 4.1 Routing and Planning Flow

The system uses a 3-step routing check before planning:

```
+-------------------------------------------------------------------+
|                    STAGE 0: ROUTING CHECK                          |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
| 3-Step Routing Decision:                                           |
|                                                                    |
| Step 1: Write Detection                                            |
|   - Does task require file modifications (Write/Edit)?             |
|   - YES → Continue to Step 2                                       |
|   - NO → Route to breadth-reader skill (read-only)                 |
|                                                                    |
| Step 2: Breadth Task Detection                                     |
|   - Is this a breadth task (analyze many files)?                   |
|   - YES → Route to breadth-reader skill                            |
|   - NO → Continue to Step 3                                        |
|                                                                    |
| Step 3: Route Decision                                             |
|   - Simple task? → DIRECT EXECUTION (bypass planning)              |
|   - Complex task? → Enter plan mode (EnterPlanMode)                |
+-------------------------------------------------------------------+
                              |
                    [If routed to plan mode]
                              |
+-------------------------------------------------------------------+
|                    STAGE 1: PLANNING                               |
|                    (native plan mode)                              |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
| Plan mode (unified analysis + planning)                            |
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
|    - Implementation tasks: N items per agent decomposition         |
| 5. Map dependencies                                                |
| 6. Build parallelization plan (more tasks, fewer waves)            |
| 7. Flag risks                                                      |
|                                                                    |
| Output: Structured execution plan with TaskCreate calls            |
+-------------------------------------------------------------------+
                              |
+-------------------------------------------------------------------+
|                    STAGE 2: EXECUTION                              |
+-------------------------------------------------------------------+
                              |
| Main Claude (with workflow_orchestrator system prompt)             |
|                                                                    |
| Processing:                                                        |
| 1. Execute Wave N phases (spawn via Task)                          |
|    - Batched if phases > CLAUDE_MAX_CONCURRENT                     |
| 2. Wait for completion notifications (NO TaskOutput/TaskList poll) |
| 3. Read scratchpad files for context                               |
| 4. Execute Wave N+1 with context                                   |
| 5. Final verification wave                                         |
| 6. Provide summary                                                 |
|                                                                    |
| Agent Return Protocol:                                             |
| - Agents write output to $CLAUDE_SCRATCHPAD_DIR                    |
| - Agents return: DONE|{path} (minimal response only)               |
| - TaskOutput is PROHIBITED (context exhaustion)                    |
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
| breadth-reader (skill) | analyze, explore, read-only | Read, Glob, Grep | Breadth tasks (many files) |
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

### 4.5 Subagent vs Team Mode Selection

The planning phase evaluates a `team_mode_score` to decide the execution mechanism.

**Prerequisites:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` must be set. Otherwise, subagent mode is always used.

**Scoring Factors:**

| Factor | Points | Condition |
|--------|--------|-----------|
| Phase count | +2 | > 8 phases |
| Complexity tier | +2 | Tier 3 (score > 15) |
| Cross-phase data flow | +3 | Phase B reads and makes decisions based on Phase A output |
| Review-fix cycles | +3 | Plan includes review/verify then fix/refactor on same artifact |
| Iterative refinement | +2 | Plan includes success criterion with retry loops |
| User keyword | +5 | User says "collaborate", "team", "work together" |
| Breadth task | -5 | Same operation across multiple items |
| Phase count <= 3 | -3 | Simple workflow |

**Decision:** Score >= 5 selects team mode. Score < 5 selects subagent mode.

**The ONE parameter difference:**
- `Task(team_name="project-team", ...)` = **teammate** (shared context, SendMessage, shared task list)
- `Task(...)` = **isolated subagent** (no communication, no coordination)

---

## Section 5: State Management

### 5.1 State File Architecture

```
.claude/
  state/
    delegated_sessions.txt     # Session registry
    active_delegations.json    # Parallel execution tracking
    active_task_graph.json     # Current execution plan
    team_mode_active           # Signals hooks that Agent Teams mode is active
    team_config.json           # Active team configuration (name, teammates, roles)
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
  "delegation_active": true,
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

**Batched Execution:** When a wave has more parallel phases than `max_concurrent`, phases are executed in batches to prevent context exhaustion.

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

## Section 6: Dual-Mode Execution Philosophy

### 6.1 Why Two Modes?

The framework supports two execution mechanisms because workflows have fundamentally different coordination needs:

| Characteristic | Subagent Mode | Team Mode |
|----------------|---------------|-----------|
| Communication | None (isolated) | Peer-to-peer via SendMessage |
| Context sharing | Scratchpad files only | Shared task list + messaging |
| Coordination | Wave-based (lead controls) | Self-organizing (teammates coordinate) |
| Overhead | Minimal (no team setup) | Higher (team creation, messaging protocol) |
| Best for | Independent parallel work | Collaborative, iterative work |

**Subagent mode** is the right default. Most workflows consist of independent tasks that can be parallelized without inter-agent communication. The wave system handles dependencies naturally: Wave N+1 starts after Wave N completes, with context passed via scratchpad files.

**Team mode** becomes valuable when the work is inherently collaborative -- when agents need to react to each other's findings, negotiate design decisions, or iterate on shared artifacts. Forcing these patterns through sequential wave execution adds unnecessary latency and loses the benefits of real-time coordination.

### 6.2 Design Trade-offs

**Subagent mode advantages:**
- Context efficiency: Each agent's full transcript stays isolated; main agent sees only `DONE|{path}`
- Deterministic execution: Wave ordering provides predictable behavior
- Simpler state management: No team lifecycle, no messaging protocol
- Easier debugging: Each agent's output is self-contained in a scratchpad file

**Team mode advantages:**
- Real-time coordination: Teammates can message each other without waiting for wave completion
- Adaptive execution: Teammates can self-organize based on discovered complexity
- Shared awareness: All teammates see the shared task list, enabling dynamic work claiming
- Review-fix cycles: A reviewer can immediately notify an implementer, who fixes without wave overhead

**Team mode costs:**
- Lead context pressure: Team messages flow through the lead agent's context
- Non-deterministic execution: Teammate ordering depends on runtime conditions
- More complex state: `team_mode_active`, `team_config.json`, shutdown protocol
- Recovery complexity: Failed teammates require explicit shutdown and cleanup

### 6.3 The Conservative Selection Principle

The `team_mode_score` algorithm is deliberately conservative. The threshold (>= 5) requires strong signals before activating team mode:

- A simple "collaborate" keyword (+5) grants immediate access, respecting user intent
- Without user intent, the workflow itself must demonstrate need: complex (Tier 3: +2), many phases (>8: +2), cross-phase data flow (+3), or review-fix cycles (+3)
- Counter-signals actively suppress team mode: breadth tasks (-5), simple workflows (-3)
- The env var `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` acts as a hard gate -- without it, team mode is never considered

This ensures team mode activates only when its coordination benefits outweigh its overhead costs.

### 6.4 Two Team Workflow Patterns

**Simple team (single AGENT TEAM phase):**
- Use case: Multi-perspective exploration (e.g., "analyze from different angles")
- Structure: One phase with `phase_type: "team"` and a `teammates` array
- Each teammate entry becomes a separate `Task(team_name=...)` invocation
- Teammates explore in parallel, then a synthesis phase aggregates findings

**Complex team (multiple phases across waves):**
- Use case: Collaborative implementation (e.g., "implement project collaboratively")
- Structure: Standard multi-wave plan with individual phases, but `execution_mode: "team"` at the plan level
- Every phase executes as a teammate via `Task(team_name=...)` instead of isolated `Task(...)`
- Teammates share context and can message each other within the same wave

The key insight: the plan structure (phases, waves, dependencies) remains identical between modes. Only the execution mechanism changes -- one parameter (`team_name`) on every `Task` call.

### 6.5 Team Lifecycle

```
User Request
    |
Plan mode evaluates team_mode_score
    |
Score >= 5 + AGENT_TEAMS env var set?
├── NO → Subagent mode (standard pipeline)
└── YES → Team mode:
         |
    Step 0: Create team — TeamCreate(team_name="workflow-{timestamp}")
         |
    Step 1: For each wave:
         |   Spawn teammates via Task(team_name=...) in parallel
         |   Wait for completion notifications
         |
    Step 2: Monitor (teammates self-coordinate via SendMessage)
         |
    Step 3: Shutdown (SendMessage shutdown_request to each teammate)
         |
    Step 4: Cleanup
         |   - TaskUpdate for completed phases
         |   - Remove .claude/state/team_mode_active
         |   - Remove .claude/state/team_config.json
         |   - Report final status
```

### 6.6 Agent COMMUNICATION MODE

All 8 specialized agents include a conditional COMMUNICATION MODE section in their system prompts:

- **As a teammate** (Agent Teams active): Write output to scratchpad, send brief completion messages to teammates, proactively message teammates when discovering cross-cutting issues
- **As a subagent** (default): Return exactly `DONE|{output_file_path}` -- no summaries, no explanations, only the path

This dual behavior is encoded in each agent's `.md` configuration file, ensuring the same agent can operate in either mode without modification.

### 6.7 Hook Enforcement in Team Mode

The PreToolUse hook adapts its behavior when team mode is active:

- **`validate_task_graph_compliance.py`**: Bypassed entirely. Team mode handles dependencies through teammate coordination rather than strict wave ordering
- **`require_delegation.py`**: Auto-provisions the `team_mode_active` state file when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set and a team tool (TeamCreate, SendMessage, or Task with team_name) is invoked. Also adds Agent Teams tools (TeamCreate, SendMessage) to the allowlist
- **Pattern matching**: Any tool name containing "team" or "teammate" (case-insensitive) is allowed as a safety net

---

## Section 7: Emergent Properties

### 7.1 Self-Organizing Workflow

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

### 7.2 Fail-Safe Behaviors

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

### 7.3 Observability

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

### 7.4 Resilience Properties

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
|  Skills: breadth-reader | Planning: native plan mode                     |
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
|  |                    3-Step Routing Check                           |  |
|  |  Write Detection -> Breadth Task -> Route Decision                |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    Plan Mode (native, unified)                   |  |
|  |  Intent Parsing -> Decomposition -> Agent Selection -> Waves      |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    breadth-reader (skill)                         |  |
|  |  Read-only analysis for breadth tasks (many files)                |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    workflow_orchestrator (system prompt)          |  |
|  |  Batched Execution -> Scratchpad Context -> Verification          |  |
|  +-------------------------------------------------------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                    Execution Mode Selection                       |  |
|  |  Subagent (default): Task() -> isolated agents                    |  |
|  |  Team (experimental): TeamCreate + Task(team_name) -> teammates   |  |
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
|    delegated_sessions.txt    (session registry, legacy)                 |
|    active_delegations.json   (parallel exec, delegation_active flag)    |
|    active_task_graph.json    (execution plan)                           |
|    team_mode_active          (team mode signal, auto-created by hook)   |
|    team_config.json          (team name, teammates, role mappings)      |
|  $CLAUDE_SCRATCHPAD_DIR/                                                 |
|    {phase_id}.md             (agent output scratchpad files)            |
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
