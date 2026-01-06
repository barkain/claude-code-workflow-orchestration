# Architecture Quick Reference Guide

> Fast-access reference for the Claude Code Workflow Orchestration System.
> For comprehensive documentation, see [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md).

---

## Table of Contents

1. [Decision Trees](#decision-trees)
2. [Agent Reference Tables](#agent-reference-tables)
3. [State File Reference](#state-file-reference)
4. [Hook Reference](#hook-reference)
5. [Debugging Checklists](#debugging-checklists)
6. [Common Patterns](#common-patterns)

---

## Decision Trees

### Should I Use /delegate?

```
Is the task blocked by PreToolUse hook?
├── YES → Use /delegate immediately
│         Do NOT try alternative tools
│
└── NO → Is task multi-step?
         ├── YES → Consider workflow orchestration
         │         (append workflow_orchestrator.md)
         │
         └── NO → Is task read-only question?
                  ├── YES → Use /ask
                  │
                  └── NO → Use /delegate for execution
```

### Which Agent Will Handle My Task?

```
Count keyword matches in task description:

Does task contain >= 2 of: analyze, understand, explore, architecture, patterns, structure, dependencies?
├── YES → codebase-context-analyzer (read-only analysis)

Does task contain >= 2 of: refactor, cleanup, optimize, improve, technical debt, maintainability?
├── YES → code-cleanup-optimizer (implementation)

Does task contain >= 2 of: verify, validate, test, check, review, quality, edge cases?
├── YES → task-completion-verifier (verification)

Does task contain >= 2 of: design, approach, research, evaluate, best practices, architect?
├── YES → tech-lead-architect (design)

Does task contain >= 2 of: review, code review, critique, feedback, assess quality, evaluate code?
├── YES → code-reviewer (read-only)

Does task contain >= 2 of: setup, deploy, docker, CI/CD, infrastructure, pipeline, configuration?
├── YES → devops-experience-architect (implementation)

Does task contain >= 2 of: document, write docs, README, explain, create guide, documentation?
├── YES → documentation-expert (implementation)

Does task contain >= 2 of: dependencies, packages, requirements, install, upgrade, manage packages?
├── YES → dependency-manager (implementation)

Does task contain >= 2 of: plan, break down, subtasks, roadmap, phases, organize, milestones?
├── YES → task-decomposer (planning)

No agent >= 2 matches?
└── general-purpose delegation
```

### Sequential vs Parallel Execution?

```
Are phases dependent?
├── Phase B reads files from Phase A? → SEQUENTIAL
├── Both phases modify same file? → SEQUENTIAL
├── Both phases affect same state? → SEQUENTIAL
├── API rate limits apply? → SEQUENTIAL
│
└── NO dependencies detected
    └── Does task contain uppercase "AND"?
        ├── YES → Check for conflicts
        │         ├── Conflicts found → SEQUENTIAL
        │         └── No conflicts → PARALLEL
        │
        └── NO → Default to SEQUENTIAL (conservative)
```

### Is Task Atomic?

```
Is depth < 3?
├── YES → NOT ATOMIC (must decompose)

At depth >= 3, check ALL criteria:

1. Time < 30 minutes?
   └── NO → NOT ATOMIC

2. Files <= 3?
   └── NO → NOT ATOMIC

3. Single deliverable?
   └── NO → NOT ATOMIC

4. No planning required?
   └── NO → NOT ATOMIC

5. Single responsibility (no "and" connecting verbs)?
   └── NO → NOT ATOMIC

6. Expressible in 2-3 sentences?
   └── NO → NOT ATOMIC

ALL criteria met?
├── YES → ATOMIC (leaf node)
└── NO → NOT ATOMIC (decompose further)
```

---

## Agent Reference Tables

### Agent Capabilities Matrix

| Agent | Read | Write | Edit | Bash | Task | Glob | Grep |
|-------|:----:|:-----:|:----:|:----:|:----:|:----:|:----:|
| delegation-orchestrator | - | - | - | - | - | - | - |
| codebase-context-analyzer | Y | - | - | Y | - | Y | Y |
| tech-lead-architect | Y | Y | Y | Y | - | Y | Y |
| task-completion-verifier | Y | - | - | Y | - | Y | Y |
| code-cleanup-optimizer | Y | Y | Y | Y | - | Y | Y |
| code-reviewer | Y | - | - | Y | - | Y | Y |
| devops-experience-architect | Y | Y | Y | Y | - | Y | Y |
| documentation-expert | Y | Y | Y | Y | - | Y | Y |
| dependency-manager | Y | Y | Y | Y | - | - | - |
| task-decomposer | Y | - | - | - | Y | - | - |
| phase-validator | Y | - | - | Y | - | Y | Y |

**Legend:** Y = Has access, - = No access

### Agent Selection Keywords

| Agent | Primary Keywords | Secondary Keywords |
|-------|-----------------|-------------------|
| codebase-context-analyzer | analyze, architecture | understand, explore, patterns, structure, dependencies |
| code-cleanup-optimizer | refactor, optimize | cleanup, improve, technical debt, maintainability |
| task-completion-verifier | verify, validate | test, check, review, quality, edge cases |
| tech-lead-architect | design, architect | approach, research, evaluate, best practices, scalability, security |
| code-reviewer | review, code review | critique, feedback, assess quality, evaluate code |
| devops-experience-architect | deploy, docker | setup, CI/CD, infrastructure, pipeline, configuration |
| documentation-expert | document, documentation | write docs, README, explain, create guide |
| dependency-manager | dependencies, packages | requirements, install, upgrade, manage packages |
| task-decomposer | plan, break down | subtasks, roadmap, phases, organize, milestones |
| phase-validator | validate, verify phase | check completion, phase criteria |

### Agent Use Cases

| Use Case | Recommended Agent | Rationale |
|----------|------------------|-----------|
| "How does auth work?" | codebase-context-analyzer | Read-only exploration |
| "Refactor for maintainability" | code-cleanup-optimizer | Implementation focus |
| "Test the calculator" | task-completion-verifier | Verification focus |
| "Design API architecture" | tech-lead-architect | Design/planning focus |
| "Review PR changes" | code-reviewer | Objective assessment |
| "Set up Docker" | devops-experience-architect | Infrastructure focus |
| "Update README" | documentation-expert | Documentation focus |
| "Add pytest dependency" | dependency-manager | Package management |
| "Break down feature" | task-decomposer | Planning/decomposition |
| "Check phase deliverables" | phase-validator | Phase verification |

---

## State File Reference

### delegated_sessions.txt

**Location:** `.claude/state/delegated_sessions.txt`

**Format:** One session ID per line
```
sess_abc123
sess_def456
```

**Operations:**
```bash
# Check registered sessions
cat .claude/state/delegated_sessions.txt

# Clear all sessions
> .claude/state/delegated_sessions.txt

# Check if session is registered
grep "sess_abc123" .claude/state/delegated_sessions.txt
```

### active_delegations.json

**Location:** `.claude/state/active_delegations.json`

**Schema:**
```json
{
  "version": "2.0",
  "workflow_id": "wf_YYYYMMDD_HHMMSS",
  "execution_mode": "sequential|parallel",
  "active_delegations": [
    {
      "delegation_id": "deleg_YYYYMMDD_HHMMSS_NNN",
      "phase_id": "phase_N_M",
      "session_id": "sess_XXX",
      "wave": 0,
      "status": "active|completed|failed",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "agent": "agent-name"
    }
  ],
  "max_concurrent": 4
}
```

**Operations:**
```bash
# View current state
cat .claude/state/active_delegations.json | jq .

# Count active delegations
cat .claude/state/active_delegations.json | jq '.active_delegations | length'

# Find active phases
cat .claude/state/active_delegations.json | jq '.active_delegations[] | select(.status == "active")'

# Reset state
echo '{"version":"2.0","execution_mode":"sequential","active_delegations":[]}' > .claude/state/active_delegations.json
```

### active_task_graph.json

**Location:** `.claude/state/active_task_graph.json`

**Schema:**
```json
{
  "task_id": "root",
  "tier": 1|2|3,
  "complexity_score": N,
  "waves": [
    {
      "wave_id": 0,
      "parallel_execution": true|false,
      "phases": [
        {
          "phase_id": "phase_N_M",
          "type": "implementation|verification",
          "agent": "agent-name",
          "status": "pending|in_progress|completed|failed"
        }
      ]
    }
  ],
  "current_wave": 0
}
```

---

## Hook Reference

### Hook Execution Order

```
1. SessionStart       (session begins)
2. UserPromptSubmit   (before user message)
3. PreToolUse         (before each tool)
4. [Tool Executes]
5. PostToolUse        (after each tool)
6. SubagentStop       (subagent completes)
7. Stop               (session ends)
```

### Hook Quick Reference

| Hook | Trigger | Key Actions | Timeout |
|------|---------|-------------|---------|
| SessionStart | startup, resume, clear, compact | Inject workflow_orchestrator.md | 20s |
| UserPromptSubmit | Before user message | Clear delegated_sessions.txt | 2s |
| PreToolUse (*) | Before every tool | Validate task graph, check allowlist | 5s each |
| PostToolUse (Write/Edit) | After Python file changes | Ruff + Pyright validation | default |
| PostToolUse (Task) | After Task tool | Depth validation, wave update, DAG viz | 5-10s each |
| SubagentStop | Subagent completes | Todo reminder, verification trigger | 2-5s each |
| Stop | Session ends | Cleanup stale sessions | default |

### Allowlist Reference

**Always Allowed (no delegation required):**
- `AskUserQuestion` - Read-only questions
- `TodoWrite` - Task tracking
- `SlashCommand` - Triggers session registration
- `Task`/`SubagentTask`/`AgentTask` - Delegation mechanism

**Blocked Until Delegated:**
- Read, Write, Edit, MultiEdit
- Glob, Grep
- Bash
- NotebookEdit
- All other tools

---

## Debugging Checklists

### Tools Not Working

- [ ] Is session registered? Check `.claude/state/delegated_sessions.txt`
- [ ] Was `/delegate` used? Use it immediately when blocked
- [ ] Are hooks installed? Check `ls -la ~/.claude/hooks/*/`
- [ ] Are hooks executable? Run `chmod +x ~/.claude/hooks/*/*.sh`
- [ ] Check hook syntax: `bash -n <hook_script>`
- [ ] Enable debug logging: `export DEBUG_DELEGATION_HOOK=1`
- [ ] Tail debug log: `tail -f /tmp/delegation_hook_debug.log`

### Delegation Failing

- [ ] Is delegation-orchestrator agent file present? Check `~/.claude/agents/delegation-orchestrator.md`
- [ ] Are other agent files present? Check `ls ~/.claude/agents/`
- [ ] Is settings.json configured? Check `cat ~/.claude/settings.json | jq '.hooks'`
- [ ] Reinstall if needed: `cp -r agents hooks ~/.claude/`

### Multi-Step Not Detected

- [ ] Is workflow_orchestrator.md appended? Use `--append-system-prompt`
- [ ] Does task have multi-step indicators?
  - Sequential connectors: "and then", "with", "including"
  - Multiple verbs: "create", "test", "verify"
  - Phase markers: "first... then..."
- [ ] Try explicit phrasing: "Create X and then test X"

### Parallel Not Working

- [ ] Does task contain uppercase "AND"?
- [ ] Are phases truly independent (no data dependencies)?
- [ ] Are phases modifying different files?
- [ ] Check `active_delegations.json` for execution_mode
- [ ] Orchestrator may default to sequential (conservative)

### Python Validation Failing

- [ ] Is Ruff installed? Run `which ruff` or `uvx ruff --version`
- [ ] Is Pyright installed? Run `which pyright` or `npx pyright --version`
- [ ] Check specific error in PostToolUse output
- [ ] Skip validation if needed: `export CHECK_RUFF=0` or `export CHECK_PYRIGHT=0`

### StatusLine Not Updating

- [ ] Is statusline script installed? Check `ls -la ~/.claude/scripts/statusline.sh`
- [ ] Is script executable? Run `chmod +x ~/.claude/scripts/statusline.sh`
- [ ] Does state file exist? Check `ls -la .claude/state/active_delegations.json`
- [ ] Is JSON valid? Run `cat .claude/state/active_delegations.json | jq .`

---

## Common Patterns

### Basic Delegation

```bash
# Single task
/delegate Create a calculator.py with add and subtract functions

# Read-only question
/ask How does the authentication system work?

# Pre-commit checks
/pre-commit
```

### Multi-Step Workflow

```bash
# Append orchestrator and run workflow
claude --append-system-prompt "$(cat ~/.claude/system-prompts/workflow_orchestrator.md)" \
  "Create calculator.py with tests and verify they pass"
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Run delegation
/delegate Create test.py

# Watch logs (separate terminal)
tail -f /tmp/delegation_hook_debug.log
```

### Emergency Bypass

```bash
# Disable delegation (emergency only)
export DELEGATION_HOOK_DISABLE=1

# Run direct commands
claude "Create file directly"

# Re-enable immediately
export DELEGATION_HOOK_DISABLE=0
```

### Reset All State

```bash
# Clear session registry
> .claude/state/delegated_sessions.txt

# Reset active delegations
echo '{"version":"2.0","execution_mode":"sequential","active_delegations":[]}' > .claude/state/active_delegations.json

# Remove task graph
rm -f .claude/state/active_task_graph.json
```

### Monitor Workflow

```bash
# Watch status (separate terminal)
watch -n 1 ~/.claude/scripts/statusline.sh

# View current state
cat .claude/state/active_delegations.json | jq .

# Check recent events
tail -20 /tmp/claude_session_log.txt
```

---

## Complexity Scoring Quick Reference

### Formula

```
score = file_count*2 + lines/50 + concerns*1.5 + ext_deps + (arch_decisions ? 3 : 0)
```

### Tier Thresholds

| Tier | Score Range | Minimum Depth | Description |
|------|-------------|---------------|-------------|
| 1 | < 5 | 1 | Simple (utility, config) |
| 2 | 5-15 | 2 | Moderate (module, endpoint) |
| 3 | > 15 | 3 | Complex (feature, system) |

**Sonnet Override:** All tasks → Tier 3 (depth >= 3)

### Quick Estimates

| Task Type | Typical Score | Tier |
|-----------|---------------|------|
| "Create hello.py" | ~3 | 1 |
| "Create calculator with tests" | ~8 | 2 |
| "Implement auth endpoint with JWT" | ~12 | 2 |
| "Migrate monolith to microservices" | ~40+ | 3 |
| "Build notification system with SMS/email/push" | ~28 | 3 |

---

## Environment Variables Quick Reference

| Variable | Default | Enable | Purpose |
|----------|---------|--------|---------|
| `DEBUG_DELEGATION_HOOK` | 0 | `=1` | Hook debug logging |
| `DELEGATION_HOOK_DISABLE` | 0 | `=1` | Emergency bypass |
| `CLAUDE_PROJECT_DIR` | `$PWD` | `=/path` | State file location |
| `CHECK_RUFF` | 1 | `=0` | Skip Ruff validation |
| `CHECK_PYRIGHT` | 1 | `=0` | Skip Pyright validation |

---

## Related Documentation

- [Architecture Philosophy](./ARCHITECTURE_PHILOSOPHY.md) - Comprehensive design documentation
- [Hook Debugging Guide](./hook-debugging.md) - Detailed hook troubleshooting
- [Environment Variables](./environment-variables.md) - Full configuration reference
- [StatusLine System](./statusline-system.md) - Status display documentation
- [Python Coding Standards](./python-coding-standards.md) - Code quality requirements
- [Main Documentation](../CLAUDE.md) - Project overview
