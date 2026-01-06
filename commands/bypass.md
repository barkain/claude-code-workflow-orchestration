---
allowed-tools: AskUserQuestion, Bash
model: haiku
---

# Delegation Bypass Toggle

This command allows you to toggle the delegation enforcement system on or off within the current session.

## Instructions

1. **Check Current State**: First, check if the delegation bypass is currently active by testing if the flag file exists:
   ```bash
   test -f .claude/state/delegation_disabled && echo "DISABLED" || echo "ENABLED"
   ```

2. **Determine Current Status**:
   - If the command outputs "DISABLED": Delegation is currently bypassed (hooks are not enforcing)
   - If the command outputs "ENABLED": Delegation is currently active (hooks are enforcing)

3. **Present Options to User**: Use AskUserQuestion to show the current state and offer options:
   - Current state: [Delegation ENABLED/DISABLED]
   - Options:
     - "Disable delegation (bypass hooks)" - Creates the flag file, hooks will allow all tools
     - "Enable delegation (enforce hooks)" - Removes the flag file, hooks will enforce allowlist

4. **Handle User Choice**:

   **If user selects "Disable delegation"**:
   - Check if `.claude/state/delegation_disabled` already exists
   - If exists: Report "No change needed - delegation bypass is already active"
   - If not exists:
     - Ensure directory exists: `mkdir -p .claude/state`
     - Create flag file: `touch .claude/state/delegation_disabled`
     - Report "Delegation bypass ENABLED - hooks will allow all tools"

   **If user selects "Enable delegation"**:
   - Check if `.claude/state/delegation_disabled` exists
   - If not exists: Report "No change needed - delegation enforcement is already active"
   - If exists:
     - Remove flag file: `rm .claude/state/delegation_disabled`
     - Report "Delegation enforcement ENABLED - hooks will enforce allowlist"

## Security Note

This bypass is session-scoped and intended for debugging or emergency situations. The flag file is checked by the PreToolUse hook (`require_delegation.sh`) to determine whether to enforce the delegation policy.

## Usage

```
/bypass
```

The command will interactively guide you through checking and toggling the delegation state.
