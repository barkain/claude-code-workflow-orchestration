# Deprecated Files

## orchestration-reminder.py

**Status**: DEPRECATED (as of November 2025)

**Original Purpose**: This Python script was previously used as a UserPromptSubmit hook to remind Claude Code about orchestration patterns.

**Why Deprecated**:
- The delegation workflow has evolved to use bash-based hooks for better performance and simplicity
- Session state is now managed through `clear-delegation-sessions.sh`
- Python dependency introduced unnecessary complexity for simple file operations

**Migration**:
- Functionality replaced by `clear-delegation-sessions.sh`
- No action required - file can remain for historical reference or be safely deleted

**Safe to Delete**: Yes, this file is no longer referenced in settings.json or any active hooks.

---

## Active Hooks

Current UserPromptSubmit hooks:
- ✅ `clear-delegation-sessions.sh` - Clears stale delegation session state on every user prompt
