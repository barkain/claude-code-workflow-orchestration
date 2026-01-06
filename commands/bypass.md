---
allowed-tools: AskUserQuestion, Bash
model: haiku
---

# Bypass - Toggle Delegation Enforcement

Toggle delegation enforcement on/off for this session.

## Instructions

1. Use AskUserQuestion to prompt the user with these options:
   - Question: "Toggle delegation enforcement:"
   - Option 1: "Disable delegation (allow all tools)" - description: "Creates bypass flag, tools will not be blocked"
   - Option 2: "Enable delegation (enforce hooks)" - description: "Removes bypass flag, normal enforcement applies"

2. Based on user selection:

   **If user selected "Disable delegation":**
   - Run: `mkdir -p .claude/state && touch .claude/state/delegation_disabled`
   - If file already existed, report: "Bypass already active - no change needed"
   - If file was created, report: "✓ Delegation bypass enabled - all tools now allowed"

   **If user selected "Enable delegation":**
   - Run: `rm -f .claude/state/delegation_disabled`
   - Report: "✓ Delegation enforcement enabled - normal hook restrictions apply"

## Notes
- The bypass flag persists until explicitly toggled
- This is for debugging/troubleshooting within a session
