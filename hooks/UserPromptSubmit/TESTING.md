# UserPromptSubmit Hook Testing Guide

## Quick Verification

### 1. Check Installation
```bash
# Verify hook exists and is executable
ls -lah /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh

# Should show: -rwxr-xr-x (executable permissions)
```

### 2. Verify Syntax
```bash
# Check bash script has no syntax errors
bash -n /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh
# Should complete silently (no output = success)
```

### 3. Test Manual Execution
```bash
# Create a test session file
mkdir -p /Users/user/.claude/state
echo "test-session-123" > /Users/user/.claude/state/delegated_sessions.txt

# Run the hook manually
/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh

# Verify file was deleted
test -f /Users/user/.claude/state/delegated_sessions.txt && echo "FAIL: File still exists" || echo "PASS: File cleared"
```

### 4. Test with Debug Logging
```bash
# Enable debug mode
export DEBUG_DELEGATION_HOOK=1

# Create test file again
echo "test-session-456" > /Users/user/.claude/state/delegated_sessions.txt

# Run hook
/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh

# Check debug log
tail -20 /tmp/delegation_hook_debug.log
```

Expected debug output:
```
[UserPromptSubmit] 2025-11-09 18:59:30 - Starting session cleanup
[UserPromptSubmit] 2025-11-09 18:59:30 - SUCCESS: Cleared delegation sessions file: /Users/user/.claude/state/delegated_sessions.txt
[UserPromptSubmit] 2025-11-09 18:59:30 - Session cleanup completed successfully
```

## Integration Testing

### Test Hook Fires on User Prompt

1. **Start Claude Code conversation**
2. **Use /delegate to create a session** (this will add session to delegated_sessions.txt)
3. **Submit new user prompt** (hook should fire and clear sessions)
4. **Try to use a tool directly** (should be blocked - session cleared)

### Verify Hook Configuration

```bash
# Check settings.json contains UserPromptSubmit configuration
grep -A 10 "UserPromptSubmit" /Users/user/.claude/settings.json
```

Expected output:
```json
"UserPromptSubmit":
[
    {
        "hooks":
        [
            {
                "type": "command",
                "command": "/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh",
                "timeout": 2
            }
        ]
    }
]
```

## Troubleshooting

### Problem: Hook not firing

**Symptoms**: Delegation sessions persist across user prompts

**Checks**:
```bash
# 1. Verify hook is registered in settings.json
grep -q "UserPromptSubmit" /Users/user/.claude/settings.json && echo "✓ Hook registered" || echo "✗ Hook NOT registered"

# 2. Verify script is executable
test -x /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh && echo "✓ Executable" || echo "✗ NOT executable"

# 3. Check for syntax errors
bash -n /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh
```

**Solutions**:
- Make script executable: `chmod +x /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh`
- Restart Claude Code CLI
- Check Claude Code logs for hook errors

### Problem: Permission denied

**Symptoms**: Hook fails to delete file

**Debug**:
```bash
# Enable debug logging
export DEBUG_DELEGATION_HOOK=1

# Check state directory permissions
ls -lad /Users/user/.claude/state/

# Check file permissions
ls -la /Users/user/.claude/state/delegated_sessions.txt
```

**Solutions**:
```bash
# Fix directory permissions
chmod 755 /Users/user/.claude/state/

# Fix file permissions (if it exists)
chmod 644 /Users/user/.claude/state/delegated_sessions.txt
```

### Problem: Hook timeout

**Symptoms**: Claude Code waits too long for hook to complete

**Current timeout**: 2 seconds (configured in settings.json)

**Debug**:
```bash
# Measure hook execution time
time /Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh
```

**Expected**: < 0.1 seconds (should be nearly instant)

**Solution**: If hook takes >1 second, check:
- Disk I/O performance
- State directory on slow network mount?
- Increase timeout in settings.json (not recommended - fix root cause)

### Problem: Hook disabled unintentionally

**Symptoms**: Hook doesn't run, no errors

**Check**:
```bash
# Verify bypass is not enabled
echo $DELEGATION_HOOK_DISABLE
# Should be empty or "0"
```

**Solution**:
```bash
# If set to "1", unset it
unset DELEGATION_HOOK_DISABLE
```

## Debug Mode Reference

### Enable Debug Logging
```bash
export DEBUG_DELEGATION_HOOK=1
```

### View Debug Logs
```bash
# Real-time monitoring
tail -f /tmp/delegation_hook_debug.log

# Last 50 lines
tail -50 /tmp/delegation_hook_debug.log

# Search for errors
grep -i "error\|fail\|warning" /tmp/delegation_hook_debug.log
```

### Clear Debug Logs
```bash
# Clean slate for new test session
rm -f /tmp/delegation_hook_debug.log
```

## Emergency Bypass

If the hook is causing issues and blocking Claude Code:

```bash
# Disable ALL delegation hooks temporarily
export DELEGATION_HOOK_DISABLE=1

# Use Claude Code normally (no delegation enforcement)

# Re-enable when ready
unset DELEGATION_HOOK_DISABLE
```

**WARNING**: Only use bypass for troubleshooting. Delegation hooks provide important workflow enforcement.

## Health Check Script

Save this as `/Users/user/.claude/hooks/UserPromptSubmit/healthcheck.sh`:

```bash
#!/usr/bin/env bash
# Quick health check for UserPromptSubmit hook system

echo "=== UserPromptSubmit Hook Health Check ==="
echo

# Check 1: Hook exists
if [[ -f "/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh" ]]; then
  echo "✓ Hook file exists"
else
  echo "✗ Hook file MISSING"
  exit 1
fi

# Check 2: Executable
if [[ -x "/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh" ]]; then
  echo "✓ Hook is executable"
else
  echo "✗ Hook NOT executable"
  exit 1
fi

# Check 3: Syntax valid
if bash -n "/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh" 2>/dev/null; then
  echo "✓ Bash syntax valid"
else
  echo "✗ Bash syntax ERROR"
  exit 1
fi

# Check 4: Registered in settings
if grep -q "clear-delegation-sessions.sh" /Users/user/.claude/settings.json 2>/dev/null; then
  echo "✓ Hook registered in settings.json"
else
  echo "✗ Hook NOT registered in settings.json"
  exit 1
fi

# Check 5: State directory writable
if [[ -w "/Users/user/.claude/state" ]]; then
  echo "✓ State directory writable"
else
  echo "⚠ State directory not writable (may cause issues)"
fi

echo
echo "=== All checks passed ==="
exit 0
```

Run health check:
```bash
chmod +x /Users/user/.claude/hooks/UserPromptSubmit/healthcheck.sh
/Users/user/.claude/hooks/UserPromptSubmit/healthcheck.sh
```
