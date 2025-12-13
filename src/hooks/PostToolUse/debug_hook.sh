#!/usr/bin/env bash
#
# debug_hook.sh - Debug hook to capture what Claude Code provides
#
# Purpose: Log all environment variables and stdin data to understand
# what Claude Code actually passes to PostToolUse hooks

DEBUG_LOG="/tmp/posttooluse_debug.log"

# Simple file creation to confirm hook is running
touch /tmp/hook_was_called_$(date +%s).marker

{
    echo "==================== PostToolUse Hook Debug ===================="
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""

    echo "=== Environment Variables (CLAUDE_*) ==="
    env | grep -E "^CLAUDE_" || echo "No CLAUDE_* environment variables found"
    echo ""

    echo "=== stdin JSON Input (RAW) ==="
    # Read stdin and save it
    STDIN_DATA=$(cat)
    echo "$STDIN_DATA"
    echo ""

    echo "=== Parsed JSON (Pretty Print) ==="
    if echo "$STDIN_DATA" | python3 -m json.tool 2>/dev/null; then
        echo "JSON is valid and formatted above"
    else
        echo "JSON is invalid or empty"
    fi
    echo ""

    echo "=== Extract Fields from JSON ==="
    TOOL_NAME=$(echo "$STDIN_DATA" | grep -o '"tool_name":"[^"]*"' | sed 's/"tool_name":"\([^"]*\)"/\1/' || echo "NOT_FOUND")
    TOOL_STATUS=$(echo "$STDIN_DATA" | grep -o '"status":"[^"]*"' | sed 's/"status":"\([^"]*\)"/\1/' || echo "NOT_FOUND")
    SESSION_ID=$(echo "$STDIN_DATA" | grep -o '"session_id":"[^"]*"' | sed 's/"session_id":"\([^"]*\)"/\1/' || echo "NOT_FOUND")

    echo "tool_name: $TOOL_NAME"
    echo "status: $TOOL_STATUS"
    echo "session_id: $SESSION_ID"
    echo ""

    echo "==================== End Debug ===================="
    echo ""
} >> "$DEBUG_LOG" 2>&1

# Always exit 0 to not block execution
exit 0
