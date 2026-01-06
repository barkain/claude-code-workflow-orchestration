---
allowed-tools: AskUserQuestion, Task
model: haiku
---

# Bypass - Toggle Delegation Enforcement

Toggle delegation enforcement on/off for this session.

## Instructions

1. Use AskUserQuestion to prompt the user:
   - Question: "Toggle delegation enforcement:"
   - Option 1: "Disable delegation (allow all tools)" - description: "Creates bypass flag, tools will not be blocked"
   - Option 2: "Enable delegation (enforce hooks)" - description: "Removes bypass flag, normal enforcement applies"

2. Based on user selection, use Task tool to perform the action:

   **If user selected "Disable delegation":**
   Use Task with general-purpose agent and haiku model:
   ```
   Create the bypass flag file by running:
   mkdir -p .claude/state && touch .claude/state/delegation_disabled

   Report whether the file was created or already existed.
   ```

   **If user selected "Enable delegation":**
   Use Task with general-purpose agent and haiku model:
   ```
   Remove the bypass flag file by running:
   rm -f .claude/state/delegation_disabled

   Report that delegation enforcement is now enabled.
   ```

3. Confirm the action to the user.

## Notes
- The bypass flag persists until explicitly toggled
- This is for debugging/troubleshooting within a session
