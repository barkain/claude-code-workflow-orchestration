---
description: Intelligently delegate tasks to specialized agents with multi-step detection
argument-hint: [task description]
allowed-tools: Task
---

# Intelligent Task Delegation

**USER TASK:** $ARGUMENTS

---

## How This Works

This command uses a **two-stage delegation architecture**:

### Stage 1: Orchestration (Analysis & Planning)
The **delegation-orchestrator** agent analyzes your task to:
- Determine if single-step or multi-step workflow
- Select the most appropriate specialized agent(s)
- Construct optimized delegation prompts
- Return structured recommendation

### Stage 2: Execution (Delegation)
The **main agent** (you are reading this now) receives the orchestrator's recommendation and:
- Parses the delegation prompt from recommendation
- Executes final delegation to specialized agent(s)
- Manages multi-step context passing (if applicable)
- Reports results to user

---

## Available Specialized Agents

The orchestrator has access to these specialized agents:

- **codebase-context-analyzer** - Code exploration, architecture analysis, dependency mapping
- **task-decomposer** - Project planning, task breakdown, dependency sequencing
- **tech-lead-architect** - Solution design, technology research, architectural decisions
- **task-completion-verifier** - Validation, testing, quality assurance, verification
- **code-cleanup-optimizer** - Code refactoring, quality improvement, technical debt reduction
- **devops-experience-architect** - Infrastructure, deployment, containerization, CI/CD pipelines

---

## Execution Process

### Step 1: Get Orchestration Recommendation

Spawn the delegation-orchestrator agent directly.
The orchestrator agent will automatically load its system prompt and:
- Analyze task complexity (multi-step vs single-step)
- Select the most appropriate specialized agent(s)
- Construct optimized delegation prompts
- Return structured recommendation

The recommendation will be in this format:
```markdown
## ORCHESTRATION RECOMMENDATION

### Task Analysis
- Type: [Single-step / Multi-step]
- Complexity: [description]

### Agent Selection (for single-step) OR Phase Breakdown (for multi-step)
...

### Delegation Prompt
```
[Complete prompt ready for delegation]
```

### Execution Instructions for Main Agent
[Natural language instructions for spawning the appropriate agent]
```

### Step 2: Parse Recommendation

Extract from orchestrator's output:

**For Single-Step Tasks:**
- Look for "### Delegation Prompt" section
- Extract the complete prompt between the code fence markers
- This is the prompt to provide when spawning the specialized agent

**For Multi-Step Tasks:**
- Look for "#### Phase 1:" section
- Find "**Phase 1 Delegation Prompt:**" subsection
- Extract the complete prompt between the code fence markers
- Note the context passing requirements for subsequent phases

### Step 3: Execute Delegation

**For Single-Step Tasks:**

Spawn the appropriate specialized agent directly using the extracted delegation prompt. Simply provide the delegation prompt from the orchestrator's recommendation to the main agent, which will automatically interpret and spawn the correct subagent using Claude's built-in subagent system.

**For Multi-Step Tasks:**

Execute Phase 1 first by spawning the appropriate specialized agent directly with the Phase 1 delegation prompt. The main agent will automatically interpret and spawn the correct subagent using Claude's built-in subagent system.

After Phase 1 completes:

1. **Capture context** from Phase 1 results:
   - File paths created/modified (absolute paths)
   - Key decisions made
   - Configurations determined
   - Issues encountered
   - Specific artifacts to reference

2. **Go back to orchestrator** for Phase 2 guidance:
   - Spawn the delegation-orchestrator agent directly
   - Provide user task + context from Phase 1
   - Request Phase 2 recommendation

   **Example: Re-invoking Orchestrator for Phase 2**

   After Phase 1 completes, invoke the orchestrator again by spawning the delegation-orchestrator agent directly with the following prompt structure:

   ```
   **ORIGINAL USER TASK:** $ARGUMENTS

   **COMPLETED PHASES:**

   Phase 1: [Phase name, e.g., 'Research & Analysis']
   Agent Used: [Agent name, e.g., 'tech-lead-architect']
   Results:
   - Created file: /absolute/path/to/file.ext
   - Key decisions: [List decisions made, e.g., 'Selected FastAPI framework', 'Chose PostgreSQL database']
   - Implementation approach: [Describe approach used, e.g., 'Layered architecture with service pattern']
   - Configurations determined: [List any configs, e.g., 'Python 3.12+, async/await patterns']
   - Issues encountered: [Note any blockers/resolutions, e.g., 'None' or 'Resolved dependency conflict']

   **REQUEST:**

   Please provide Phase 2 recommendation based on the completed Phase 1 context above. Use the Phase 2 template from your multi-step breakdown and fill in the specific context from Phase 1 results.
   ```

   This prompt includes:
   - The original user task for reference
   - Complete context from Phase 1 (files created, decisions, approach)
   - Clear request for Phase 2 guidance with Phase 1 context

   **Key Points:**
   - Always use **absolute file paths** when referencing files created in previous phases
   - Capture **specific decisions** (framework choices, architectural patterns, etc.)
   - Note any **blockers or issues** encountered and how they were resolved
   - Include **configuration details** that affect subsequent phases

3. **Parse Phase 2 recommendation** and execute

4. **Repeat** for all remaining phases

### Step 4: Report Results

Provide the user with:

**For Single-Step Tasks:**
- Summary of what agent handled the task
- Key outcomes and deliverables
- Any notable decisions made
- Next steps (if applicable)

**For Multi-Step Tasks:**
- Summary of each completed phase
- Context passed between phases
- Final deliverables across all phases
- Overall workflow completion status

---

## Multi-Step Context Passing Protocol

When executing multi-step workflows, always capture and pass this context between phases:

**Required Context:**
- **File paths** created or modified (use absolute paths)
- **Key decisions** made during the phase
- **Configurations** or settings determined
- **Issues** encountered and how resolved
- **Specific artifacts** to reference in next phase

**Example Context Format:**
```
Context from Phase 1 (Research):
- Analyzed documentation at https://example.com/docs
- Key finding: Plugin system uses event-driven architecture
- Identified 3 core extension points: hooks, filters, middleware
- Created research notes: /tmp/research_notes.md
```

This context gets included in the next orchestrator call to inform Phase 2 planning.

---

## Error Handling

### If Orchestrator Recommendation Parsing Fails
- Look for delegation instructions in the recommendation
- Use those as fallback guidance
- If no clear instructions, ask user for clarification

### If Orchestrator Agent Fails to Load
- Claude Code will report the error
- Fall back to manual agent selection if needed
- Ask user for clarification on how to proceed

### If Multi-Step Phase Fails
- Stop the workflow at the failing phase
- Report which phase failed and why
- Ask user whether to retry the phase or abort workflow
- Do not proceed to next phase without user confirmation

---

## Best Practices

1. **Always parse carefully** - Extract exact prompt from recommendation code fences
2. **Preserve prompt structure** - Use delegation prompt exactly as provided by orchestrator
3. **Track context diligently** - In multi-step workflows, capture comprehensive context
4. **Report transparently** - Let user know which agents handled which parts
5. **Handle errors gracefully** - Stop and ask user before proceeding after failures

---

## Begin Delegation

Execute the delegation process now using Steps 1-4 above.

**Important Reminders:**
- You will spawn agents twice in the process:
  1. First spawn the delegation-orchestrator agent directly (get recommendation)
  2. Then spawn the specialized agent directly (execute delegation)
- For multi-step: Spawn the orchestrator agent again for each subsequent phase
- Parse the delegation prompt from orchestrator's structured output
- Use the extracted prompt verbatim when spawning the specialized agent
- The main agent will automatically interpret your instructions and spawn the correct subagents using Claude's built-in subagent system
