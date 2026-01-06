#!/usr/bin/env bash
# ============================================================================
# UserPromptSubmit Hook: Clear Delegation Sessions
# ============================================================================
# Purpose: Clear stale delegation session state on every user prompt
#
# This hook ensures that delegation state doesn't persist across user
# interactions, forcing explicit /delegate usage for each workflow.
#
# Timing: Fires BEFORE each user message is processed by Claude Code
# ============================================================================

set -euo pipefail

# Resolve plugin directory (works both in development and when installed)
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# --- Configuration ---
STATE_DIR="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/state"
DELEGATED_SESSIONS_FILE="$STATE_DIR/delegated_sessions.txt"
DELEGATION_FLAG_FILE="$STATE_DIR/delegation_active"  # FIX: Subagent session inheritance flag
ACTIVE_DELEGATIONS_FILE="$STATE_DIR/active_delegations.json"
VALIDATION_DIR="$STATE_DIR/validation"
GATE_LOG_FILE="$VALIDATION_DIR/gate_invocations.log"

# Memory management configuration
MAX_LOG_SIZE=1048576                    # 1MB threshold for log rotation
MAX_ROTATIONS=5                         # Keep 5 backup copies
VALIDATION_FILE_MAX_AGE_HOURS=24        # Delete validation files older than 24 hours

DEBUG_HOOK="${DEBUG_DELEGATION_HOOK:-0}"
DEBUG_FILE="/tmp/delegation_hook_debug.log"

# --- Debug logging function ---
debug_log() {
  if [[ "$DEBUG_HOOK" == "1" ]]; then
    echo "[UserPromptSubmit] $(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$DEBUG_FILE"
  fi
}

# --- Emergency bypass (for troubleshooting) ---
if [[ "${DELEGATION_HOOK_DISABLE:-0}" == "1" ]]; then
  debug_log "Hook disabled via DELEGATION_HOOK_DISABLE=1"
  exit 0
fi

# Check for in-session delegation disable flag (do not clear this flag - it persists)
if [[ -f "${STATE_DIR}/delegation_disabled" ]]; then
    [[ "${DEBUG_DELEGATION_HOOK:-0}" == "1" ]] && echo "[DEBUG] Delegation disabled via flag file, skipping session clearing" >> /tmp/delegation_hook_debug.log
    exit 0
fi

# ============================================================================
# Memory Management Functions
# ============================================================================

# --- Function: Rotate log file when it exceeds size threshold ---
rotate_log() {
  local log_file="$1"

  # Check if log file exists
  if [[ ! -f "$log_file" ]]; then
    debug_log "Log rotation skipped: $log_file does not exist"
    return 0
  fi

  # Get file size (cross-platform: BSD stat on macOS, GNU stat on Linux)
  local file_size
  if stat --version &>/dev/null; then
    # GNU stat (Linux)
    file_size=$(stat -c %s "$log_file" 2>/dev/null || echo "0")
  else
    # BSD stat (macOS)
    file_size=$(stat -f %z "$log_file" 2>/dev/null || echo "0")
  fi

  # Check if rotation needed
  if [[ "$file_size" -lt "$MAX_LOG_SIZE" ]]; then
    debug_log "Log rotation not needed: $log_file ($file_size bytes < $MAX_LOG_SIZE threshold)"
    return 0
  fi

  debug_log "Rotating log file: $log_file ($file_size bytes >= $MAX_LOG_SIZE threshold)"

  # Rotate existing backups (delete oldest if MAX_ROTATIONS reached)
  for ((i=MAX_ROTATIONS-1; i>=1; i--)); do
    local old_backup="${log_file}.${i}"
    local new_backup="${log_file}.$((i+1))"

    if [[ -f "$old_backup" ]]; then
      if [[ $i -eq $((MAX_ROTATIONS-1)) ]]; then
        # Delete oldest backup
        rm -f "$new_backup" 2>/dev/null || true
        debug_log "Deleted oldest rotation: $new_backup"
      fi
      mv "$old_backup" "$new_backup" 2>/dev/null || true
      debug_log "Rotated: $old_backup -> $new_backup"
    fi
  done

  # Move current log to .1
  mv "$log_file" "${log_file}.1" 2>/dev/null || {
    debug_log "WARNING: Failed to rotate log file (permissions?)"
    return 0  # Non-fatal error
  }

  # Create new empty log file with same permissions
  touch "$log_file" 2>/dev/null || true
  chmod 644 "$log_file" 2>/dev/null || true

  debug_log "Log rotation completed: $log_file -> ${log_file}.1"
  return 0
}

# --- Function: Cleanup old validation state files ---
cleanup_old_validations() {
  local validation_dir="$1"

  # Check if validation directory exists
  if [[ ! -d "$validation_dir" ]]; then
    debug_log "Validation cleanup skipped: $validation_dir does not exist"
    return 0
  fi

  debug_log "Starting validation state cleanup in: $validation_dir"

  # Calculate age threshold in seconds
  local max_age_seconds=$((VALIDATION_FILE_MAX_AGE_HOURS * 3600))
  local current_time=$(date +%s)
  local deleted_count=0

  # Find and delete old .json validation files
  while IFS= read -r -d '' file; do
    # Get file modification time (cross-platform)
    local file_mtime
    if stat --version &>/dev/null; then
      # GNU stat (Linux)
      file_mtime=$(stat -c %Y "$file" 2>/dev/null || echo "0")
    else
      # BSD stat (macOS)
      file_mtime=$(stat -f %m "$file" 2>/dev/null || echo "0")
    fi

    # Skip if we couldn't get mtime
    if [[ "$file_mtime" == "0" ]]; then
      debug_log "WARNING: Could not get mtime for: $file"
      continue
    fi

    # Calculate file age
    local file_age=$((current_time - file_mtime))

    # Delete if older than threshold
    if [[ "$file_age" -gt "$max_age_seconds" ]]; then
      if rm -f "$file" 2>/dev/null; then
        ((deleted_count++))
        debug_log "Deleted old validation file (age: ${file_age}s): $file"
      else
        debug_log "WARNING: Failed to delete: $file"
      fi
    fi
  done < <(find "$validation_dir" -type f -name "*.json" -print0 2>/dev/null || true)

  debug_log "Validation cleanup completed: deleted $deleted_count files older than ${VALIDATION_FILE_MAX_AGE_HOURS}h"
  return 0
}

# --- Function: Prune stale entries from active_delegations.json ---
prune_active_delegations() {
  local delegations_file="$1"

  # Check if file exists
  if [[ ! -f "$delegations_file" ]]; then
    debug_log "Active delegations pruning skipped: file does not exist"
    return 0
  fi

  # Check if file is empty
  if [[ ! -s "$delegations_file" ]]; then
    debug_log "Active delegations pruning skipped: file is empty"
    return 0
  fi

  debug_log "Pruning stale entries from: $delegations_file"

  # Simple approach: delete entire file if it exists (sessions are cleared on each prompt)
  # This is safe because all sessions are invalidated by delegated_sessions.txt cleanup
  if rm -f "$delegations_file" 2>/dev/null; then
    debug_log "Cleared active delegations file (all sessions invalidated)"
  else
    debug_log "WARNING: Failed to clear active delegations file"
  fi

  return 0
}

# ============================================================================
# Main Execution: Session Cleanup + Memory Management
# ============================================================================

debug_log "Starting session cleanup and memory management"

# 1. Clear delegation sessions (existing behavior)
if [[ -f "$DELEGATED_SESSIONS_FILE" ]]; then
  # Attempt to remove the file
  if rm -f "$DELEGATED_SESSIONS_FILE" 2>/dev/null; then
    debug_log "SUCCESS: Cleared delegation sessions file: $DELEGATED_SESSIONS_FILE"
  else
    # Log error but don't fail the hook - Claude Code should continue
    debug_log "WARNING: Failed to remove file (permissions?): $DELEGATED_SESSIONS_FILE"
    # Exit 0 to not block Claude Code
    exit 0
  fi
else
  debug_log "INFO: No delegation sessions file to clear (already clean)"
fi

# 1.5. FIX: Clear delegation flag for subagent session inheritance
if [[ -f "$DELEGATION_FLAG_FILE" ]]; then
  if rm -f "$DELEGATION_FLAG_FILE" 2>/dev/null; then
    debug_log "SUCCESS: Cleared delegation_active flag: $DELEGATION_FLAG_FILE"
  else
    debug_log "WARNING: Failed to remove delegation_active flag: $DELEGATION_FLAG_FILE"
  fi
fi

# 2. Prune stale active delegations
prune_active_delegations "$ACTIVE_DELEGATIONS_FILE"

# 3. Rotate gate invocations log if needed
rotate_log "$GATE_LOG_FILE"

# 4. Cleanup old validation state files
cleanup_old_validations "$VALIDATION_DIR"

# --- Clean exit ---
debug_log "Session cleanup and memory management completed successfully"
exit 0
