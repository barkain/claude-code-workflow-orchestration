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

This is not merely a software architecture pattern - it is a fundamental insight about how to harness AI capabilities effectively:

```
Traditional Model:  Agent -> [All Tools] -> Results
                    (Unfocused, shallow execution)

Constrained Model:  Agent -> [Delegation] -> [Specialized Agents] -> [Deep Execution] -> Results
                    (Focused, deep execution with verification)
```

### 1.2 Why Constraints Enable Better Outcomes

**1.2.1 Depth Over Breadth**

When an agent has unlimited tool access, it tends toward shallow, immediate solutions. The constraint of delegation forces:
- Task decomposition before execution
- Explicit planning through TodoWrite
- Verification phases for every implementation
- Context preservation between phases

**1.2.2 Specialization Through Restriction**

Each specialized agent has a restricted tool set that matches its domain:

| Agent Type | Tool Access | Why |
|------------|-------------|-----|
| Read-Only (analyzer, reviewer) | Read, Glob, Grep, Bash | Objectivity requires inability to modify |
| Implementation (optimizer, devops) | Read, Write, Edit, Glob, Grep, Bash | Can modify but cannot spawn sub-delegations |
| Meta-Agents (orchestrator, decomposer) | Read, Task, TodoWrite | Coordinates but doesn't execute directly |
| Verification (verifier, validator) | Read, Bash, Glob, Grep | Validates without modifying (maintains objectivity) |

**1.2.3 Security Through Transparency**

The hook system creates an auditable trail of all tool invocations:
- Every tool attempt is logged (with DEBUG_DELEGATION_HOOK=1)
- Session registration is explicit and traceable
- State is cleared between user prompts (no privilege persistence)
- Stale sessions are automatically cleaned up

### 1.3 The Capability-Constraint Spectrum

```
                    CONSTRAINT LEVEL
    Low ←───────────────────────────────────→ High

    Direct    Limited    Delegation    Full
    Access    Allowlist  Required      Restriction

    ↓         ↓          ↓             ↓

    Shallow   Some       Deep          Analysis
    Execution Planning   Execution     Only

    Fast,     Moderate   Thorough,     Safe,
    Risky     Balance    Verified      Passive
```

The Workflow Orchestration System operates in the "Delegation Required" zone, optimizing for thorough, verified execution while maintaining practical usability.

### 1.4 Core Design Principles

**Principle 1: Explicit Over Implicit**
- All delegations must be explicitly invoked via `/delegate`
- Session privileges are explicitly granted through hook registration
- Context is explicitly passed between phases (no hidden state)

**Principle 2: Verification as First-Class Citizen**
- Every workflow has minimum 2 phases (implementation + verification)
- Verification agents cannot modify code (objectivity guarantee)
- Failed verification blocks workflow progression

**Principle 3: Conservative Defaults**
- Sequential execution is the default (safer)
- Parallel execution requires explicit independence confirmation
- When in doubt, decompose further

**Principle 4: Transparency at Every Layer**
- Debug logging available for all hooks
- State files are human-readable (JSON, text)
- StatusLine provides real-time visibility

### 1.5 Architectural Boundaries

The system establishes clear boundaries that cannot be crossed:

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER PROMPT BOUNDARY                          │
│  (Delegation state cleared, fresh session for each prompt)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN CLAUDE SESSION                           │
│  Allowlist: TodoWrite, AskUserQuestion, SlashCommand, Task       │
│  All other tools: BLOCKED                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        /delegate
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DELEGATION BOUNDARY                           │
│  Session registered → Tool access granted                        │
│  Specialized agent spawned via Task tool                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SPECIALIZED AGENT                             │
│  Tools restricted to agent's declared capabilities               │
│  Cannot spawn nested delegations (prevents recursion)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 2: The Three Pillars

The system's reliability and effectiveness rest on three foundational pillars: Context Isolation, Workflow Governance, and Quality Gates.

### 2.1 Pillar One: Context Isolation

**2.1.1 Definition**

Context Isolation ensures that each component of the system operates with only the information and capabilities it needs, preventing unintended state leakage and maintaining clear responsibility boundaries.

**2.1.2 Isolation Mechanisms**

**Session Isolation:**
```
User Prompt 1 ──┬── Session A ──┬── Tool Access
                │               └── State Files
                │
                └── [UserPromptSubmit clears state]

User Prompt 2 ──┬── Session B ──┬── Tool Access (fresh)
                │               └── State Files (fresh)
```

**Agent Isolation:**
- Each specialized agent runs in its own subagent context
- Agents cannot directly communicate (only through explicit context passing)
- Agent tool sets are declared and enforced via frontmatter

**State Isolation:**
- `.claude/state/delegated_sessions.txt` - Session registry (cleared per prompt)
- `.claude/state/active_delegations.json` - Parallel execution tracking (workflow scoped)
- No global mutable state that persists across user prompts

**2.1.3 Context Passing Protocol**

When context must flow between phases, it follows a strict protocol:

```
Phase N Completion
        ↓
┌───────────────────────────────────────┐
│         Context Capture               │
│  - File paths (absolute only)         │
│  - Key decisions made                 │
│  - Issues encountered                 │
│  - Artifacts created                  │
└───────────────────────────────────────┘
        ↓
TodoWrite Update (Phase N → completed)
        ↓
┌───────────────────────────────────────┐
│         Context Injection             │
│  "Context from Phase N:"              │
│  - Created: /absolute/path/file.py    │
│  - Decision: Used type hints          │
│  - Issue: None                        │
└───────────────────────────────────────┘
        ↓
Phase N+1 Delegation
```

**2.1.4 Benefits of Context Isolation**

| Benefit | Description |
|---------|-------------|
| Predictability | Each component behaves consistently regardless of previous operations |
| Debuggability | Problems can be traced to specific sessions/phases |
| Security | No privilege escalation through state manipulation |
| Reproducibility | Same input produces same delegation behavior |

### 2.2 Pillar Two: Workflow Governance

**2.2.1 Definition**

Workflow Governance ensures that multi-step tasks are decomposed, scheduled, and executed in a controlled manner with appropriate checkpoints and verification gates.

**2.2.2 Governance Mechanisms**

**Complexity Scoring:**
```python
complexity_score = (
    file_count * 2 +
    estimated_lines / 50 +
    distinct_concerns * 1.5 +
    external_dependencies +
    (architecture_decisions ? 3 : 0)
)

tier = (
    1 if complexity_score < 5 else      # Simple
    2 if complexity_score <= 15 else    # Moderate
    3                                    # Complex
)
```

**Tier-Based Minimum Depths:**

| Tier | Complexity Score | Minimum Depth | Rationale |
|------|------------------|---------------|-----------|
| 1 | < 5 | 1 | Simple tasks need minimal decomposition |
| 2 | 5-15 | 2 | Moderate tasks need component separation |
| 3 | > 15 | 3 | Complex tasks need granular atomic units |

**Sonnet Model Override:**
For claude-sonnet models, all tasks are forced to Tier 3 (depth >= 3) regardless of calculated complexity score. This ensures thorough decomposition for models that benefit from explicit task breakdown.

**2.2.3 Wave Scheduling**

For parallel execution, tasks are organized into waves:

```
Wave 0 (Parallel)
├── Phase 0.0: Create auth.py
├── Phase 0.1: Create utils.py
└── Phase 0.2: Create config.py
        ↓
    [Wave Sync: All Wave 0 phases complete]
        ↓
Wave 1 (Parallel)
├── Phase 1.0: Verify auth.py
├── Phase 1.1: Verify utils.py
└── Phase 1.2: Verify config.py
        ↓
    [Wave Sync: All Wave 1 phases complete]
        ↓
Wave 2 (Sequential)
└── Phase 2.0: Integration tests
```

**Wave Validation Rules:**
1. Implementation and verification phases cannot be in the same wave
2. No phase can depend on another phase within the same parallel wave
3. Phases modifying the same file cannot be in the same parallel wave

**2.2.4 Atomicity Enforcement**

Tasks marked as atomic must satisfy ALL criteria:

**Quantitative:**
- Time: < 30 minutes
- Files: <= 3 files
- Deliverable: Exactly 1 primary output

**Qualitative:**
- No further planning required
- Single responsibility
- Self-contained
- Expressible in 2-3 sentences

**Red Flags (automatic non-atomic):**
- Contains "with" followed by noun
- Contains "and" connecting verbs
- Contains plural nouns ("operations", "functions")
- Mentions multiple files
- Estimated time > 15 minutes
- Description > 10 words

### 2.3 Pillar Three: Quality Gates

**2.3.1 Definition**

Quality Gates are mandatory checkpoints that ensure code quality, security, and correctness before workflow progression.

**2.3.2 Pre-Execution Gates**

**PreToolUse Hook Gate:**
```
Tool Invocation Request
        ↓
┌───────────────────────────────────────┐
│      Task Graph Compliance Check      │
│  - Phase ID exists in execution plan? │
│  - Phase wave matches current wave?   │
│  - Dependencies satisfied?            │
└───────────────────────────────────────┘
        ↓ (PASS)            ↓ (FAIL)
┌───────────────────┐  ┌───────────────────┐
│ Delegation Check  │  │ BLOCK execution   │
│ - Session in      │  │ Return error      │
│   registry?       │  │                   │
│ - Tool allowed?   │  │                   │
└───────────────────┘  └───────────────────┘
```

**2.3.3 Post-Execution Gates**

**PostToolUse Python Validation:**
```
Write/Edit on .py file
        ↓
┌───────────────────────────────────────┐
│     Critical Security Check           │
│  - No pickle.loads() on user input    │
│  - No exec()/eval() on user input     │
│  - No hardcoded secrets               │
└───────────────────────────────────────┘
        ↓ (PASS)
┌───────────────────────────────────────┐
│          Ruff Validation              │
│  - Syntax checking                    │
│  - Security rules (S codes)           │
│  - Style enforcement                  │
└───────────────────────────────────────┘
        ↓ (PASS)
┌───────────────────────────────────────┐
│        Pyright Type Checking          │
│  - Type annotation validation         │
│  - Type inference checks              │
└───────────────────────────────────────┘
```

**2.3.4 Verification Phase Gate**

Every implementation phase is followed by a verification phase:

```
Implementation Phase Complete
        ↓
┌───────────────────────────────────────┐
│    Deliverable Manifest Check         │
│  - Files exist at expected paths?     │
│  - Functions implemented as specified?│
│  - Tests passing (if applicable)?     │
│  - Acceptance criteria met?           │
└───────────────────────────────────────┘
        ↓
    Verification Verdict:
    - PASS → Proceed to next phase
    - PASS_WITH_MINOR_ISSUES → Proceed with notes
    - FAIL → Re-implement with remediation steps
```

**2.3.5 Quality Gate Summary**

| Gate | Trigger | Validates | Blocks If |
|------|---------|-----------|-----------|
| PreToolUse | Before every tool | Session, allowlist, task graph | Not delegated or out of sequence |
| PostToolUse (Python) | After Write/Edit .py | Syntax, security, types | Validation fails |
| PostToolUse (Task Graph) | After Task | Depth >= 3 for atomic tasks | Insufficient decomposition |
| Verification Phase | After implementation | Deliverable manifest | Acceptance criteria not met |

---

## Section 3: Hook System Behavior

### 3.1 The 6-Hook Lifecycle

The system implements a comprehensive 6-hook architecture that governs the entire session lifecycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                      SESSION LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────┘

1. SessionStart
   ├── Trigger: Session begins (startup, resume, clear, compact)
   ├── Action: Inject workflow orchestrator system prompt
   └── Output: Session initialized with delegation capabilities

2. UserPromptSubmit
   ├── Trigger: Before each user message
   ├── Action: Clear delegation state (.claude/state/delegated_sessions.txt)
   └── Output: Fresh session state (no privilege persistence)

3. PreToolUse (matcher: *)
   ├── Trigger: Before EVERY tool invocation
   ├── Actions:
   │   ├── validate_task_graph_compliance.sh - Check phase ordering
   │   └── require_delegation.sh - Enforce allowlist, register sessions
   └── Output: Allow or block tool execution

4. PostToolUse
   ├── Matcher: Edit|Write|MultiEdit
   │   └── python_posttooluse_hook.sh - Validate Python code
   ├── Matcher: Task
   │   ├── validate_task_graph_depth.sh - Enforce depth-3 minimum
   │   └── remind_todo_after_task.sh - Prompt TodoWrite update
   └── Output: Validated code, task completion reminders

5. SubagentStop
   ├── Trigger: When subagent completes
   ├── Actions:
   │   ├── remind_todo_update.sh - Prompt task list update
   │   ├── trigger_verification.sh - Trigger verification phase
   │   └── clear-delegation-sessions.sh - Clean up subagent session
   └── Output: Wave synchronization, verification triggers

6. Stop
   ├── Trigger: Session ends
   ├── Action: python_stop_hook.sh - Cleanup stale sessions
   └── Output: Clean state for next session
```

### 3.2 Hook Execution Order

When multiple hooks are registered for the same event, they execute in registration order:

```
PreToolUse (* matcher):
    1. validate_task_graph_compliance.sh  (timeout: 5s)
    2. require_delegation.sh               (timeout: 5s)

    First hook failure blocks subsequent hooks and tool execution.
```

### 3.3 Hook Communication

Hooks communicate through:

**Environment Variables:**
- `CLAUDE_SESSION_ID` - Current session identifier
- `CLAUDE_TOOL_NAME` - Tool being invoked
- `CLAUDE_TOOL_ARGUMENTS` - JSON arguments to tool
- `CLAUDE_PARENT_SESSION_ID` - Parent session (for subagents)
- `CLAUDE_PROJECT_DIR` - Project directory override

**State Files:**
- `.claude/state/delegated_sessions.txt` - One session ID per line
- `.claude/state/active_delegations.json` - Workflow execution state
- `.claude/state/active_task_graph.json` - Current execution plan

**Exit Codes:**
- `0` - Success (allow operation to proceed)
- `1` - Failure (block operation)
- `2` - Skip (proceed without processing)

**Output Streams:**
- `stdout` - Messages shown to user
- `stderr` - Error messages and blocking reasons

### 3.4 Session Registration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION REGISTRATION                          │
└─────────────────────────────────────────────────────────────────┘

1. User invokes /delegate
   ↓
2. PreToolUse hook triggered for SlashCommand
   ↓
3. SlashCommand in allowlist → ALLOW
   ↓
4. Hook writes session ID to delegated_sessions.txt
   ↓
5. /delegate spawns delegation-orchestrator via Task
   ↓
6. PreToolUse hook triggered for Task
   ↓
7. Task in allowlist → ALLOW, register subagent session
   ↓
8. Subagent session ID added to delegated_sessions.txt
   ↓
9. Subagent has full tool access (inherited privileges)
```

### 3.5 Hook Debugging

Enable comprehensive hook debugging:

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Watch debug log
tail -f /tmp/delegation_hook_debug.log

# Log format:
# [TIMESTAMP] SESSION=ID TOOL=Name STATUS=allowed|blocked REASON=...
```

**Debug Log Examples:**
```
[2025-01-11 14:30:22] SESSION=sess_abc123 TOOL=Read STATUS=blocked REASON=not_delegated
[2025-01-11 14:30:23] SESSION=sess_abc123 TOOL=SlashCommand STATUS=allowed REASON=allowlist
[2025-01-11 14:30:23] SESSION=sess_abc123 REGISTERED REASON=delegation_trigger
[2025-01-11 14:30:24] SESSION=sess_abc123 TOOL=Task STATUS=allowed REASON=registered
[2025-01-11 14:30:25] SESSION=sess_def456 TOOL=Read STATUS=allowed REASON=inherited
```

---

## Section 4: Agent Orchestration Behavior

### 4.1 Two-Stage Delegation Architecture

The system uses a two-stage architecture for task execution:

```
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: ORCHESTRATION                        │
│                    (Analysis & Planning)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               delegation-orchestrator                            │
│                                                                  │
│  Inputs:                                                         │
│  - User task description                                         │
│  - Available agent configurations                                │
│                                                                  │
│  Processing:                                                     │
│  1. Complexity analysis (scoring formula)                        │
│  2. Tier classification (1, 2, or 3)                            │
│  3. Multi-step detection (connectors, verbs)                    │
│  4. Agent selection (keyword matching >= 2)                      │
│  5. Dependency analysis (sequential vs parallel)                │
│  6. Wave scheduling (if parallel)                               │
│  7. Deliverable manifest construction                           │
│                                                                  │
│  Outputs:                                                        │
│  - Execution plan JSON                                          │
│  - Phase delegation prompts                                      │
│  - Agent assignments                                            │
│  - Wave breakdown                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: EXECUTION                            │
│                    (Delegation)                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               Main Claude (Workflow Orchestrator)                │
│                                                                  │
│  Processing:                                                     │
│  1. Parse orchestrator's execution plan JSON                    │
│  2. Write plan to .claude/state/active_task_graph.json          │
│  3. Create TodoWrite task list                                  │
│  4. Execute Wave 0 phases (spawn via Task)                      │
│  5. Wait for wave sync (all phases complete)                    │
│  6. Capture context from completed phases                       │
│  7. Execute Wave 1 phases with context                          │
│  8. Repeat until all waves complete                             │
│  9. Provide final summary                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent Selection Algorithm

**Step 1: Keyword Extraction**
```python
task_keywords = set(task.lower().split())
# Remove common words
task_keywords -= {"the", "a", "an", "to", "for", "with", "and", "or"}
```

**Step 2: Match Counting**
```python
for agent in available_agents:
    matches = len(task_keywords & set(agent.activation_keywords))
    agent.match_count = matches
```

**Step 3: Threshold Application**
```python
candidates = [a for a in agents if a.match_count >= 2]
if not candidates:
    return "general-purpose"
return max(candidates, key=lambda a: a.match_count)
```

### 4.3 Available Agents Reference

| Agent | Keywords | Tool Access | Use Case |
|-------|----------|-------------|----------|
| delegation-orchestrator | delegate, orchestrate, route task, intelligent delegation | TodoWrite, AskUserQuestion | Meta-agent for routing |
| codebase-context-analyzer | analyze, understand, explore, architecture, patterns, structure, dependencies | Read, Glob, Grep, Bash | Code exploration |
| tech-lead-architect | design, approach, research, evaluate, best practices, architect, scalability, security | Read, Write, Edit, Glob, Grep, Bash | Solution design |
| task-completion-verifier | verify, validate, test, check, review, quality, edge cases | Read, Bash, Glob, Grep | QA and validation |
| code-cleanup-optimizer | refactor, cleanup, optimize, improve, technical debt, maintainability | Read, Write, Edit, Glob, Grep, Bash | Code improvement |
| code-reviewer | review, code review, critique, feedback, assess quality, evaluate code | Read, Glob, Grep, Bash | Code review |
| devops-experience-architect | setup, deploy, docker, CI/CD, infrastructure, pipeline, configuration | Read, Write, Edit, Glob, Grep, Bash | Infrastructure |
| documentation-expert | document, write docs, README, explain, create guide, documentation | Read, Write, Edit, Glob, Grep, Bash | Documentation |
| dependency-manager | dependencies, packages, requirements, install, upgrade, manage packages | Read, Write, Edit, Bash | Package management |
| task-decomposer | plan, break down, subtasks, roadmap, phases, organize, milestones | Read, Task, TodoWrite | Project planning |
| phase-validator | validate, verify phase, check completion, phase criteria | Read, Bash, Glob, Grep | Phase validation |

### 4.4 Execution Mode Selection

**Sequential Execution Triggers:**
- Phase B reads files created by Phase A
- Both phases modify the same file
- Both phases affect the same system state
- API rate limits require sequential calls
- Dependencies unclear (conservative fallback)

**Parallel Execution Triggers:**
- Phases operate on different files/systems
- No data dependencies between phases
- Resource isolation (no file conflicts)
- Explicit "AND" hint from user (capitalized)
- Time benefit > 30% expected

**Decision Algorithm:**
```python
def select_execution_mode(phases):
    # Check for explicit parallel hint
    if "AND" in original_task:
        # Verify no conflicts
        if not has_conflicts(phases):
            return "parallel"

    # Check dependencies
    for phase_a in phases:
        for phase_b in phases:
            if has_data_dependency(phase_a, phase_b):
                return "sequential"
            if has_file_conflict(phase_a, phase_b):
                return "sequential"

    # If truly independent, allow parallel
    return "parallel"
```

### 4.5 Context Flow Between Phases

```
Phase N (Implementation)
    ↓
┌───────────────────────────────────────────────────────────────┐
│ Phase N Results:                                               │
│   Files Created:                                               │
│     - /absolute/path/to/calculator.py                         │
│   Functions Implemented:                                       │
│     - add(a: float, b: float) -> float                        │
│     - subtract(a: float, b: float) -> float                   │
│   Key Decisions:                                               │
│     - Used type hints for Python 3.12+                        │
│     - Implemented error handling for division by zero         │
│   Issues Encountered:                                          │
│     - None                                                     │
└───────────────────────────────────────────────────────────────┘
    ↓
TodoWrite Update: Phase N complete, Phase N+1 in_progress
    ↓
Phase N+1 (Verification) Delegation Prompt:
    ↓
┌───────────────────────────────────────────────────────────────┐
│ Verify the calculator implementation at:                       │
│ /absolute/path/to/calculator.py                               │
│                                                                │
│ Context from Phase N:                                          │
│ - Functions: add, subtract (type-hinted)                       │
│ - Error handling for division by zero                          │
│                                                                │
│ Deliverable Manifest:                                          │
│ {                                                              │
│   "files": [{"path": "calculator.py", "must_exist": true}],   │
│   "tests": [...],                                              │
│   "acceptance_criteria": [...]                                 │
│ }                                                              │
└───────────────────────────────────────────────────────────────┘
```

---

## Section 5: State Management

### 5.1 State File Architecture

```
.claude/
├── state/
│   ├── delegated_sessions.txt     # Session registry
│   ├── active_delegations.json    # Parallel execution tracking
│   └── active_task_graph.json     # Current execution plan
```

### 5.2 Session Registry

**File:** `.claude/state/delegated_sessions.txt`

**Format:**
```
sess_abc123
sess_def456
sess_ghi789
```

**Lifecycle:**
1. Created when first `/delegate` triggers session registration
2. Populated with session IDs on each delegation
3. Cleared by UserPromptSubmit hook before each user prompt
4. Cleaned of stale sessions (>1 hour) by Stop hook

**Purpose:**
- Tracks which sessions have delegation privileges
- Enables tool access for registered sessions
- Prevents privilege escalation

### 5.3 Active Delegations JSON

**File:** `.claude/state/active_delegations.json`

**Schema (v2.0):**
```json
{
  "version": "2.0",
  "workflow_id": "wf_20250111_143022",
  "execution_mode": "parallel",
  "active_delegations": [
    {
      "delegation_id": "deleg_20250111_143022_001",
      "phase_id": "phase_0_0",
      "session_id": "sess_abc123",
      "wave": 0,
      "status": "active",
      "started_at": "2025-01-11T14:30:22Z",
      "agent": "codebase-context-analyzer"
    },
    {
      "delegation_id": "deleg_20250111_143023_002",
      "phase_id": "phase_0_1",
      "session_id": "sess_def456",
      "wave": 0,
      "status": "completed",
      "started_at": "2025-01-11T14:30:23Z",
      "completed_at": "2025-01-11T14:32:18Z",
      "agent": "tech-lead-architect"
    }
  ],
  "max_concurrent": 4
}
```

**Status Values:**
- `active` - Subagent currently executing
- `completed` - Subagent finished successfully
- `failed` - Subagent encountered error

### 5.4 Task Graph JSON

**File:** `.claude/state/active_task_graph.json`

**Schema:**
```json
{
  "task_id": "root",
  "description": "Original user task",
  "tier": 2,
  "complexity_score": 12,
  "waves": [
    {
      "wave_id": 0,
      "parallel_execution": true,
      "phases": [
        {
          "phase_id": "phase_0_0",
          "type": "implementation",
          "objective": "Create calculator.py",
          "agent": "code-cleanup-optimizer",
          "deliverable_manifest": {
            "files": [{"path": "calculator.py", "must_exist": false}],
            "tests": [],
            "acceptance_criteria": ["Basic math operations implemented"]
          },
          "status": "pending"
        }
      ]
    },
    {
      "wave_id": 1,
      "parallel_execution": false,
      "phases": [
        {
          "phase_id": "phase_1_0",
          "type": "verification",
          "verifies_phase_id": "phase_0_0",
          "agent": "task-completion-verifier",
          "status": "pending"
        }
      ]
    }
  ],
  "current_wave": 0
}
```

### 5.5 State Machine

```
                    USER PROMPT
                         ↓
              ┌──────────────────────┐
              │  UserPromptSubmit    │
              │  Hook: Clear State   │
              └──────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  Main Claude         │
              │  Receives Message    │
              └──────────────────────┘
                         ↓
                  Attempt Tool
                         ↓
              ┌──────────────────────┐
              │  PreToolUse Hook     │
              └──────────────────────┘
                         ↓
           ┌─────────────┴─────────────┐
           ↓                           ↓
    Session in registry?         Tool in allowlist?
           ↓                           ↓
    ┌──────┴──────┐              ┌─────┴─────┐
    ↓             ↓              ↓           ↓
   YES           NO         YES (Task/    YES (other)
    ↓             ↓         SlashCommand)     ↓
  ALLOW         BLOCK           ↓           ALLOW
                         Register + ALLOW
```

### 5.6 State Synchronization

**Wave Synchronization:**
```python
def check_wave_sync(active_delegations, current_wave):
    wave_phases = [d for d in active_delegations if d.wave == current_wave]
    completed = [d for d in wave_phases if d.status == "completed"]

    if len(completed) == len(wave_phases):
        # All phases in wave complete
        advance_wave(current_wave + 1)
        return True
    return False
```

**SubagentStop Handler:**
```python
def on_subagent_stop(session_id):
    delegation = find_delegation(session_id)
    delegation.status = "completed"
    delegation.completed_at = now()

    if check_wave_sync(active_delegations, delegation.wave):
        trigger_next_wave()
```

---

## Section 6: Emergent Properties

### 6.1 Self-Organizing Workflow

The constraint-based architecture produces emergent self-organization:

**Property 1: Automatic Verification Injection**

Every implementation phase automatically triggers a verification phase:

```
User: "Create calculator.py"
    ↓
System decomposes to:
    Phase 1: Create calculator.py (implementation)
    Phase 2: Verify calculator.py (automatic verification)
```

This emerges from the minimum 2-phase requirement, not explicit verification requests.

**Property 2: Depth-Driven Granularity**

The depth-3 minimum for atomic tasks forces meaningful decomposition:

```
User: "Create calculator with tests"
    ↓
Depth 0: Original task (non-atomic)
    ↓
Depth 1: calculator.py, test_calculator.py (non-atomic, file-level)
    ↓
Depth 2: Each file's functions (non-atomic, still grouped)
    ↓
Depth 3: Individual functions (atomic)
    - add()
    - subtract()
    - multiply()
    - divide()
    - test_add()
    - test_subtract()
    - test_multiply()
    - test_divide()
```

**Property 3: Wave-Based Concurrency Control**

The wave system automatically manages concurrency without explicit coordination:

```
Wave 0: [Phase A, Phase B, Phase C] ← All start concurrently
         ↓ (Wave sync: Wait for all)
Wave 1: [Verify A, Verify B, Verify C] ← All start after Wave 0
         ↓ (Wave sync: Wait for all)
Wave 2: [Integration] ← Starts after all verifications
```

### 6.2 Fail-Safe Behaviors

**6.2.1 Privilege Decay**

Delegation privileges automatically decay through multiple mechanisms:

1. **Session Clearing:** UserPromptSubmit clears all sessions
2. **Stale Cleanup:** Stop hook removes sessions > 1 hour old
3. **Subagent Cleanup:** SubagentStop clears subagent sessions

```
Time →
[Session Created] → [Active] → [UserPromptSubmit] → [Cleared]
                                    OR
[Session Created] → [Active] → [1 hour] → [Stop Hook] → [Removed]
```

**6.2.2 Escalation Path**

When automation fails, the system escalates to human intervention:

```
Verification FAIL (1st attempt)
    ↓
Re-implement with remediation
    ↓
Verification FAIL (2nd attempt)
    ↓
Re-implement with updated guidance
    ↓
Verification FAIL (3rd attempt)
    ↓
ESCALATE TO USER
"Maximum retries exceeded. Please review verification reports
and provide guidance for manual intervention."
```

**6.2.3 Conservative Defaults**

The system defaults to safer options when uncertain:

| Decision Point | Conservative Default |
|----------------|---------------------|
| Execution mode unclear | Sequential |
| Atomicity uncertain | Non-atomic (decompose further) |
| Tier classification ambiguous | Higher tier |
| Dependency analysis incomplete | Add dependency |

### 6.3 Composability

The architecture supports composition at multiple levels:

**6.3.1 Task Composition**

Tasks can be composed from smaller atomic units:

```
Composite Task: "Build REST API"
    ├── Atomic: Define User model
    ├── Atomic: Define Product model
    ├── Atomic: Create GET /users endpoint
    ├── Atomic: Create POST /users endpoint
    ├── Atomic: Create GET /products endpoint
    └── Atomic: Create POST /products endpoint
```

**6.3.2 Agent Composition**

Workflows can involve multiple specialized agents:

```
Workflow: "Design and implement auth system"
    ├── tech-lead-architect: Design auth architecture
    ├── task-completion-verifier: Verify design
    ├── code-cleanup-optimizer: Implement JWT middleware
    ├── task-completion-verifier: Verify implementation
    ├── documentation-expert: Document auth flow
    └── task-completion-verifier: Verify documentation
```

**6.3.3 Wave Composition**

Complex workflows compose into wave sequences:

```
Workflow: Full-stack feature
    Wave 0: [Backend models, Frontend components] (parallel)
    Wave 1: [Verify models, Verify components] (parallel)
    Wave 2: [Backend endpoints, Frontend integration]
    Wave 3: [Verify endpoints, Verify integration]
    Wave 4: [Integration tests]
    Wave 5: [Verify integration tests]
```

### 6.4 Observability

The system provides observability at every layer:

**6.4.1 StatusLine (Real-time)**
```
[PAR] Active: 2 Wave 1 | Last: codebase-context-analyzer completed (87s)
```

**6.4.2 TodoWrite (Progress Tracking)**
```json
{
  "todos": [
    {"content": "Create calculator.py", "status": "completed"},
    {"content": "Verify calculator.py", "status": "in_progress"},
    {"content": "Create tests", "status": "pending"}
  ]
}
```

**6.4.3 Debug Logging (Detailed)**
```
[14:30:22] SESSION=sess_abc TOOL=Read STATUS=blocked REASON=not_delegated
[14:30:23] SESSION=sess_abc TOOL=SlashCommand STATUS=allowed REASON=allowlist
[14:30:23] SESSION=sess_abc REGISTERED REASON=delegation_trigger
```

**6.4.4 Session Logging (Audit)**
```
[14:30:22] SESSION_START session_id=sess_abc type=main
[14:30:25] SUBAGENT_START session_id=sess_def agent=optimizer
[14:32:18] SUBAGENT_STOP session_id=sess_def duration=113s exit=0
[14:35:00] SESSION_STOP session_id=sess_abc duration=278s
```

### 6.5 Resilience Properties

**6.5.1 Idempotency**

State operations are designed to be idempotent:
- Clearing an empty registry is safe
- Adding an already-registered session is safe
- Completing an already-completed phase is safe

**6.5.2 Crash Recovery**

The system recovers gracefully from crashes:
- State files persist across restarts
- Stale sessions are cleaned automatically
- Incomplete workflows can be resumed (manual)

**6.5.3 Partial Failure Handling**

When parallel phases fail:
- Successful phases are preserved
- Failed phases can be retried independently
- Context from successful phases propagates forward

---

## Appendix A: Architectural Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW ORCHESTRATION SYSTEM                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  Commands: /delegate, /ask, /pre-commit, /list-tools                        │
│  StatusLine: [MODE] Active: N Wave W | Last: Event                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOOK SYSTEM                                     │
│  ┌────────────┐ ┌────────────────┐ ┌────────────┐ ┌────────────┐           │
│  │SessionStart│ │UserPromptSubmit│ │ PreToolUse │ │PostToolUse │           │
│  │  inject    │ │  clear state   │ │  validate  │ │  validate  │           │
│  │ orchestr.  │ │  fresh session │ │  allowlist │ │  python    │           │
│  └────────────┘ └────────────────┘ └────────────┘ └────────────┘           │
│  ┌────────────┐ ┌────────────────┐                                          │
│  │SubagentStop│ │      Stop      │                                          │
│  │wave sync   │ │ cleanup stale  │                                          │
│  └────────────┘ └────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    delegation-orchestrator                           │    │
│  │  Complexity Analysis → Agent Selection → Wave Scheduling             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    workflow_orchestrator (system prompt)             │    │
│  │  Task List → Phase Delegation → Context Passing → Verification       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPECIALIZED AGENTS                                 │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │  codebase-    │ │  tech-lead-   │ │    code-      │ │    code-      │   │
│  │  context-     │ │  architect    │ │   cleanup-    │ │   reviewer    │   │
│  │  analyzer     │ │               │ │   optimizer   │ │               │   │
│  │  (read-only)  │ │  (design)     │ │  (implement)  │ │  (read-only)  │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │    task-      │ │   devops-     │ │documentation- │ │  dependency-  │   │
│  │ completion-   │ │  experience-  │ │    expert     │ │   manager     │   │
│  │  verifier     │ │  architect    │ │               │ │               │   │
│  │  (validate)   │ │  (deploy)     │ │   (docs)      │ │  (packages)   │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│  ┌───────────────┐ ┌───────────────┐                                        │
│  │    task-      │ │    phase-     │                                        │
│  │  decomposer   │ │   validator   │                                        │
│  │   (plan)      │ │   (verify)    │                                        │
│  └───────────────┘ └───────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STATE LAYER                                     │
│  .claude/state/                                                              │
│  ├── delegated_sessions.txt    (session registry)                           │
│  ├── active_delegations.json   (parallel execution)                         │
│  └── active_task_graph.json    (execution plan)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Quick Reference Guide](./ARCHITECTURE_QUICK_REFERENCE.md) - Decision trees and checklists
- [Hook Debugging Guide](./hook-debugging.md) - Detailed hook troubleshooting
- [Environment Variables](./environment-variables.md) - Configuration options
- [StatusLine System](./statusline-system.md) - Real-time status display
- [Python Coding Standards](./python-coding-standards.md) - Code quality requirements
- [Main Documentation](../CLAUDE.md) - Project overview and usage
