# Workflow Orchestrator (Routing Stub)

## FIRST ACTION: Agent Teams Mode

The hook system pre-checks `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. You do NOT need to run any Bash commands to check it.

**Detection:** If `TeamCreate` appears in your available tools, teams are enabled. Default to team mode for ALL multi-agent work:
- Use `TeamCreate` + `Agent(team_name=...)` for ALL multi-agent work
- NEVER use isolated `Agent()` calls without `team_name`

**If `TeamCreate` is NOT in your available tools:** use parallel subagents (`Agent` without `team_name`).

---

## ROUTING (CHECK FIRST - MANDATORY)

**Four-step routing check. MUST follow this order:**

### Step 0: Team/Collaboration Detection
**Team indicators:** team, collaborate, agent team, teammate, work together, different angles, multiple perspectives, devil's advocate, brainstorm together
If ANY found: use `/delegate` to plan and execute.

### Step 1: Write Detection
**Write indicators:** create, write, save, generate, produce, output, report, build, make, implement, fix, update
If ANY found: Continue to Step 2.

### Step 2: Breadth Task Detection
**Pattern:** Same operation applied to multiple items (e.g., "review 16 files", "analyze all modules")
**Keywords:** review, analyze, summarize, scan + quantifiers like "all", "each", "files in", or explicit counts

### Step 3: Route Decision

| Pattern | Route |
|---------|-------|
| Breadth + Write (same op x many items, with output) | `/delegate` |
| Multi-phase workflow (create, test, deploy) | `/delegate` |
| Read-only breadth (no write indicators) | `/delegate` (spawns parallel Explore agents or codebase-context-analyzer) |
| Single simple task | `/delegate` |

## Always-On Delegation Mode

1. Any user request requiring work MUST be delegated to agents via `/delegate <task>`.
2. Main agent NEVER executes tools directly (except Tasks API and AskUserQuestion).
3. Full orchestrator instructions (planning, execution, agent assignment, wave scheduling) are loaded by `/delegate`.

**Agent Teams (MANDATORY when available):** If `TeamCreate` is in your available tools, ALWAYS use TeamCreate + Agent(team_name=...) for multi-agent work. Do NOT fall back to isolated parallel subagents. Teammates share context and can coordinate via SendMessage.

## Stage 1: Execution

After plan mode exits with "Status: Ready":

1. Display `STAGE 1: EXECUTION` header and render dependency graph
2. Call `TeamCreate(team_name="workflow-<timestamp>")`
3. For EACH phase: `Agent(team_name="...", subagent_type="...", prompt="...", run_in_background: true)`
4. Same wave = spawn in same message (parallel teammates)
5. Wait for completion notifications, then next wave
6. Shutdown teammates when done
7. Update task status via `TaskUpdate` after each wave

**If TeamCreate fails** (env var not set): fall back to `Agent(...)` without `team_name` (parallel subagents per wave).

## Agent Return Format
Return EXACTLY `DONE|{output_file_path}`. All content goes in the output file. No summaries.

## PROHIBITED Tools & Patterns
- **TaskOutput**: NEVER (dumps ~20K tokens)
- **TaskList polling loop**: NEVER (wait for notifications)
- Spawning > max_concurrent agents: NEVER
