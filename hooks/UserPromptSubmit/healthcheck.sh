#!/usr/bin/env bash
# ============================================================================
# Health Check: UserPromptSubmit Hook System
# ============================================================================
# Verifies that the clear-delegation-sessions hook is properly configured
# and operational.
# ============================================================================

set -euo pipefail

HOOK_FILE="/Users/user/.claude/hooks/UserPromptSubmit/clear-delegation-sessions.sh"
SETTINGS_FILE="/Users/user/.claude/settings.json"
STATE_DIR="/Users/user/.claude/state"

echo "=== UserPromptSubmit Hook Health Check ==="
echo

# Check 1: Hook exists
if [[ -f "$HOOK_FILE" ]]; then
  echo "✓ Hook file exists"
else
  echo "✗ Hook file MISSING: $HOOK_FILE"
  exit 1
fi

# Check 2: Executable
if [[ -x "$HOOK_FILE" ]]; then
  echo "✓ Hook is executable"
else
  echo "✗ Hook NOT executable (run: chmod +x $HOOK_FILE)"
  exit 1
fi

# Check 3: Syntax valid
if bash -n "$HOOK_FILE" 2>/dev/null; then
  echo "✓ Bash syntax valid"
else
  echo "✗ Bash syntax ERROR"
  bash -n "$HOOK_FILE"
  exit 1
fi

# Check 4: Registered in settings
if grep -q "clear-delegation-sessions.sh" "$SETTINGS_FILE" 2>/dev/null; then
  echo "✓ Hook registered in settings.json"
else
  echo "✗ Hook NOT registered in settings.json"
  exit 1
fi

# Check 5: State directory exists
if [[ -d "$STATE_DIR" ]]; then
  echo "✓ State directory exists"
else
  echo "⚠ State directory does not exist (will be created on demand)"
fi

# Check 6: State directory writable
if [[ -w "$STATE_DIR" ]] || [[ ! -e "$STATE_DIR" && -w "$(dirname "$STATE_DIR")" ]]; then
  echo "✓ State directory writable"
else
  echo "✗ State directory not writable: $STATE_DIR"
  exit 1
fi

# Check 7: Test execution
echo
echo "Running functional test..."
TEST_FILE="$STATE_DIR/delegated_sessions.txt"

# Create test file
mkdir -p "$STATE_DIR"
echo "test-session-healthcheck" > "$TEST_FILE"

if [[ -f "$TEST_FILE" ]]; then
  echo "✓ Test file created"
else
  echo "✗ Failed to create test file"
  exit 1
fi

# Run hook
if "$HOOK_FILE" 2>/dev/null; then
  echo "✓ Hook executed successfully"
else
  echo "✗ Hook execution failed"
  exit 1
fi

# Verify cleanup
if [[ ! -f "$TEST_FILE" ]]; then
  echo "✓ Test file cleaned up correctly"
else
  echo "✗ Test file was not removed"
  rm -f "$TEST_FILE"  # Clean up
  exit 1
fi

echo
echo "=== All checks passed ==="
echo
echo "Debug mode: export DEBUG_DELEGATION_HOOK=1"
echo "View logs: tail -f /tmp/delegation_hook_debug.log"
exit 0
