# Plan: Parallel Explore Agents for Large Data Processing

## Issue

When a user requests a large-scope read-only task (e.g., "review all files in this repo, summarize each file"), the current system either:

1. **Assigns a single agent** (Explore or code-reviewer) that sequentially reads everything, hits context limits, auto-compacts, and loses detail
2. **Assigns many specialized agents** (e.g., 15 code-reviewers in parallel) that exhaust the main agent's context when results return simultaneously

Both paths fail on large data sources.

### Root Cause

The task-planner has no awareness of:
- **Explore** as a built-in subagent (Haiku model, read-only, cheap & fast)
- **Data topology** (directory structure, file count, file sizes) as an input to decomposition
- **Aggregation** as a required final phase for distributed read-only work

### What the Docs Say

From [Claude Code subagent docs](https://code.claude.com/docs/en/sub-agents#explore):

> **Explore**: A fast, read-only agent optimized for searching and analyzing codebases.
> - Model: Haiku (fast, low-latency)
> - Tools: Read-only (denied Write/Edit)
> - Thoroughness levels: quick, medium, very thorough

> "For independent investigations, spawn multiple subagents to work simultaneously. Each subagent explores its area independently, then Claude synthesizes the findings."

> "Subagents cannot spawn other subagents."

Key properties making Explore ideal for this:
- **Cheap**: Haiku model, minimal token cost per agent
- **Fast**: Low-latency, purpose-built for search/read
- **Isolated**: Each has its own context window, won't exhaust others
- **Bounded**: Returns only a summary to the main agent

---

## Solution

Teach the task-planner to detect large-scope read-only tasks, map the data topology, and decompose into parallel Explore agents with an aggregation phase.

### Example

```
User: "Review all files in this repo. Summarize each file."

Current behavior:
  → 1 Explore agent → reads everything → hits context → auto-compacts → loses detail

Proposed behavior:
  → task-planner runs quick Explore to map topology
  → finds 6 directories, 30+ files
  → decomposes:

    Wave 0 (parallel, 6 Explore agents):
      - Explore docs/ (medium thoroughness)
      - Explore hooks/ (medium)
      - Explore agents/ (medium)
      - Explore skills/ (medium)
      - Explore commands/ (medium)
      - Explore system-prompts/ (medium)

    Wave 1 (sequential):
      - Aggregate all summaries into final report
```

### Topology-Aware Partitioning

The task-planner maps file count and sizes during its exploration step, then partitions:

| File Size | Grouping Strategy |
|-----------|-------------------|
| Small (< 200 lines) | Group 5-8 files per Explore agent |
| Medium (200-1000 lines) | Group 2-3 files per Explore agent |
| Large (> 1000 lines) | 1 file per Explore agent |

This keeps each agent within Haiku's context budget.

### Agent Selection: Explore vs Specialized

| Intent | Agent |
|--------|-------|
| "Review code for quality/security" | `code-reviewer` (needs analysis expertise) |
| "Review/summarize/explore all files" | Multiple `Explore` agents (needs breadth) |
| "Analyze architecture patterns" | `codebase-context-analyzer` (needs depth) |
| "Read and summarize large data source" | Multiple `Explore` agents (needs distribution) |

The distinction: **depth** tasks go to specialized agents, **breadth** tasks go to parallel Explore agents.

---

## Changes Required

### 1. `skills/task-planner/SKILL.md`

**Add Explore to Available Specialized Agents table:**

```markdown
| **Explore** (built-in) | review, summarize, explore, read, scan, list, catalog, inventory | Read-only codebase exploration (Haiku, fast, cheap) |
```

**Add Large Data Processing section after Atomicity Validation:**

```markdown
## Large Data Processing

When a task involves reading/reviewing/summarizing a large data source:

1. **Detect scope**: Keywords like "all files", "entire repo", "every document",
   "summarize each" signal large-scope read-only work
2. **Map topology**: Use the codebase exploration step to count files and estimate sizes
   per directory
3. **Partition**: Split into bounded chunks using topology-aware grouping
   (small files grouped, large files isolated)
4. **Assign Explore agents**: For read-only work, prefer Explore (Haiku, cheap)
   over specialized agents
5. **Add aggregation phase**: Final wave MUST synthesize results from
   all parallel Explore agents

REQUIRED: Large data processing workflows MUST include a final aggregation wave.
```

**Update Wave Optimization Rules:**

Add: "Explore agents use Haiku (cheap, fast). Higher concurrency is acceptable for Explore-only waves."

### 2. `system-prompts/workflow_orchestrator.md`

**Add Explore Agent Execution section:**

```markdown
## Explore Agent Execution

Explore is a built-in Claude Code subagent (Haiku model, read-only).

When the execution plan assigns Explore agents:
- Use `subagent_type: Explore` (NOT a custom agent name)
- Specify thoroughness in the prompt: "quick", "medium", or "very thorough"
- Explore agents are cheap (Haiku) — MAX_CONCURRENT applies but cost is minimal
- Each Explore agent returns a summary to the main agent

Example Task invocation for Explore:
  Phase ID: phase_0_1
  Agent: Explore
  Thoroughness: medium
  Scope: docs/ directory
  Task: Read and summarize all files in docs/. Return a structured summary
  with key points from each file.
```

### 3. `commands/delegate.md`

**Add note to Step 3:**

```markdown
- For Explore agents: use `subagent_type: Explore` (built-in, Haiku model).
  Do NOT use custom agent prefix `workflow-orchestrator:` for Explore.
```

---

## What Does NOT Change

- **Concurrency batching** — Already implemented (MAX_CONCURRENT=8, CLAUDE_MAX_CONCURRENT env var)
- **Input-bounded atomicity** — Already added (≤5 files or ≤10K lines per task)
- **Wave execution logic** — Explore agents execute through the same wave system
- **hooks/** — No hook changes needed
- **Other agents** — Specialized agents remain unchanged

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Large repo review completion | Fails (context exhaustion) | Completes |
| Detail retention | Lost through compaction | Preserved per-agent |
| Cost | 1 expensive agent retrying | N cheap Haiku agents |
| Speed | Sequential, slow | Parallel, fast |
| Reliability | Single point of failure | Distributed, fault-tolerant |

---

## Revised Architecture: Forked Skill Routing

### Performance Data

| Approach | Context Usage | Speed |
|----------|---------------|-------|
| Forked skill ("explore") | 30k (15%) | Fastest |
| Vanilla Claude | 33k (16%) | Fast |
| Workflow + 15 agents | 90k (45%) | Slowest |

**Key finding:** Vanilla Claude auto-optimizes breadth tasks better than forced parallelism.

### Task Type Detection

| Pattern | Route | Rationale |
|---------|-------|-----------|
| Single verb + data source | Forked skill (bypass planner) | No orchestration overhead |
| Read + action verb | Planner with forked first phase | Hybrid approach |

**Single-step examples (forked skill):**
- "review the code in ~/dev/project/"
- "explore ~/dev/project/src/"
- "summarize all files in docs/"

**Multi-step examples (planner + forked first phase):**
- "review the code and implement auth fixes"
- "explore the codebase and create architecture doc"

### Implementation Plan

1. **Create `breadth-reader` skill** with `forked: true` property
   - Receives read/explore/review prompt
   - Runs in isolated context (no main agent pollution)
   - Returns summary only

2. **Add routing logic to main agent**
   - Detect single-verb breadth tasks
   - Route to forked skill instead of planner

3. **Update task-planner for hybrid tasks**
   - Detect "read + action" patterns
   - Assign Wave 0 to forked skill
   - Continue with regular orchestration for action phases

### Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Simple breadth task context | 45-90% | 15% |
| Simple breadth task speed | Slow | 4x faster |
| Multi-step hybrid | N/A | Optimized first phase |
