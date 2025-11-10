# Workflow Orchestrator Quick Start

## Setup (One Time)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias ccw='claude --append-system-prompt "$(cat ~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md)"'
```

Then run:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

## Usage

```bash
# Use ccw for multi-step workflows
ccw "Create calculator.py and then test it"
ccw "Fix bug and verify it works"
ccw "Add logging, run tests, then commit"

# Use regular claude for single tasks
claude "Create calculator.py with tests"
```

## How to Recognize Multi-Step vs Single Task

**Multi-Step (use ccw):**
- "Create X **and then** test it"
- "Fix X, **then** verify Y"
- "Build X **and** deploy it"

**Single Task (use claude):**
- "Create X with tests" (compound task)
- "Fix and test X" (single unified task)
- "Build deployable X" (single outcome)

**Key:** Sequential connectors ("and then", "then") = multi-step workflow

## What Happens

1. **Pattern Detection:** System prompt detects multi-step pattern
2. **Task List:** Creates TodoWrite with all steps
3. **Sequential Delegation:** Delegates steps one at a time via `/delegate`
4. **Context Passing:** Each step receives context from previous steps
5. **Final Summary:** Reports all completed tasks with file paths

## Example

```bash
ccw "Create hello.py and then run it"
```

**Output:**
```
Creating task list:
1. Create hello.py (in_progress)
2. Run hello.py (pending)

Delegating task 1...
✅ Task 1 complete: Created /Users/user/hello.py

Delegating task 2 with context...
✅ Task 2 complete: Executed successfully

Final Summary:
1. ✅ Created /Users/user/hello.py
2. ✅ Executed successfully, output: "Hello, World!"
```

## Files

- **System Prompt:** `~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR.md`
- **Usage Guide:** `~/.claude/system-prompts/WORKFLOW_ORCHESTRATOR_USAGE.md`
- **Hook:** `~/.claude/hooks/PreToolUse/require_delegation.sh`

## Debug

```bash
# Enable debug mode
export DEBUG_DELEGATION_HOOK=1

# Check debug log
tail -f /tmp/delegation_hook_debug.log
```

## Emergency Bypass

```bash
# Disable hook temporarily
DELEGATION_HOOK_DISABLE=1 claude "Direct command"
```
