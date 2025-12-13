#!/bin/bash
# test_phase_a.sh - Integration tests for Phase A components

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source test utilities
source "$SCRIPT_DIR/test_utils.sh"

# Component paths
RETRY_HANDLER="$PROJECT_ROOT/hooks/PostToolUse/retry_handler.sh"
EXECUTION_LOGGER="$PROJECT_ROOT/hooks/PostToolUse/execution_logger.sh"
VIEW_EXECUTION_LOG="$HOME/.claude/scripts/view-execution-log.sh"
RETRY_MANAGER_PY="$PROJECT_ROOT/hooks/lib/retry_manager.py"
LOG_WRITER_PY="$PROJECT_ROOT/hooks/lib/log_writer.py"

# TODO: view-execution-log.sh is not yet implemented - located at $VIEW_EXECUTION_LOG
# This script provides execution log viewing and filtering functionality
if [[ ! -f "$VIEW_EXECUTION_LOG" ]]; then
    echo -e "${YELLOW}WARNING: view-execution-log.sh not found at $VIEW_EXECUTION_LOG${NC}"
    echo -e "${YELLOW}Related tests will be skipped until implementation is complete.${NC}"
fi

# ========================================
# Test Suite: retry_handler.sh
# ========================================
test_retry_handler() {
    echo -e "\n${BLUE}=== Testing retry_handler.sh ===${NC}\n"

    setup_test_env

    # Test 1: Successful tool execution (no retry triggered)
    echo -e "\n${YELLOW}Test 1: Successful tool execution${NC}"
    local session_id=$(generate_test_id)
    local workflow_id=$(generate_test_id)

    # Simulate successful tool result
    local tool_result=$(create_mock_tool_result "Read" "success" "$session_id" "$workflow_id")

    # Run retry handler
    export CLAUDE_STATE_DIR="$TEST_STATE_DIR"
    echo "$tool_result" | bash "$RETRY_HANDLER" > /dev/null 2>&1 || true

    # No retry state file should be created for success
    local retry_file="$TEST_STATE_DIR/retry_budgets.json"
    assert "No retry state created for successful tool" "[[ ! -f '$retry_file' ]]"

    # Test 2: Failed tool execution (retry state created)
    echo -e "\n${YELLOW}Test 2: Failed tool execution creates retry state${NC}"
    session_id=$(generate_test_id)
    workflow_id=$(generate_test_id)

    # Simulate failed tool result
    tool_result=$(create_mock_tool_result "Write" "error" "$session_id" "$workflow_id")

    # Run retry handler
    echo "$tool_result" | bash "$RETRY_HANDLER" > /dev/null 2>&1 || true

    # Retry state file should exist
    assert_file_exists "Retry state file created" "$retry_file"

    if [[ -f "$retry_file" ]]; then
        assert_json_valid "Retry state is valid JSON" "$retry_file"
        assert_json_key "Retry state contains session_id" "$retry_file" "$session_id"
    fi

    # Test 3: Retry budget exhaustion
    echo -e "\n${YELLOW}Test 3: Retry budget exhaustion${NC}"
    session_id=$(generate_test_id)
    workflow_id=$(generate_test_id)

    # Create retry state with max attempts
    cat > "$retry_file" <<EOF
{
  "$session_id": {
    "tool": "Edit",
    "attempts": 3,
    "max_attempts": 3,
    "last_error": "Previous error",
    "backoff_seconds": 8,
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
}
EOF

    # Simulate another failure
    tool_result=$(create_mock_tool_result "Edit" "error" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$RETRY_HANDLER" > /dev/null 2>&1 || true

    # Verify attempts not incremented beyond max
    local attempts=$(python3 -c "import json; data=json.load(open('$retry_file')); print(data.get('$session_id', {}).get('attempts', 0))" 2>/dev/null)
    assert_equals "Attempts capped at max_attempts" "3" "$attempts"

    # Test 4: Exponential backoff calculation
    echo -e "\n${YELLOW}Test 4: Exponential backoff calculation${NC}"
    session_id=$(generate_test_id)
    workflow_id=$(generate_test_id)

    # Create retry state with 1 attempt
    cat > "$retry_file" <<EOF
{
  "$session_id": {
    "tool": "Bash",
    "attempts": 1,
    "max_attempts": 3,
    "last_error": "Command failed",
    "backoff_seconds": 2,
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
}
EOF

    # Simulate another failure
    tool_result=$(create_mock_tool_result "Bash" "error" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$RETRY_HANDLER" > /dev/null 2>&1 || true

    # Verify backoff increased (2 -> 4)
    local backoff=$(python3 -c "import json; data=json.load(open('$retry_file')); print(data.get('$session_id', {}).get('backoff_seconds', 0))" 2>/dev/null)
    assert_equals "Backoff exponentially increased" "4" "$backoff"

    teardown_test_env
}

# ========================================
# Test Suite: execution_logger.sh
# ========================================
test_execution_logger() {
    echo -e "\n${BLUE}=== Testing execution_logger.sh ===${NC}\n"

    setup_test_env

    # Test 1: Log entry creation for successful tool
    echo -e "\n${YELLOW}Test 1: Log successful tool execution${NC}"
    local session_id=$(generate_test_id)
    local workflow_id=$(generate_test_id)

    # Set log directory
    export CLAUDE_LOG_DIR="$TEST_LOG_DIR"

    # Simulate successful tool result
    local tool_result=$(create_mock_tool_result "Read" "success" "$session_id" "$workflow_id")

    # Run execution logger
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Check log file created
    local log_file="$TEST_LOG_DIR/execution_${workflow_id}.jsonl"
    assert_file_exists "Execution log created" "$log_file"

    # Test 2: JSONL format validation
    echo -e "\n${YELLOW}Test 2: JSONL format validation${NC}"
    if [[ -f "$log_file" ]]; then
        # Each line should be valid JSON
        local line_count=$(wc -l < "$log_file" | tr -d ' ')
        assert_equals "Log contains 1 line" "1" "$line_count"

        # Validate JSON structure
        local first_line=$(head -n 1 "$log_file")
        echo "$first_line" > "$TEST_STATE_DIR/temp.json"
        assert_json_valid "Log entry is valid JSON" "$TEST_STATE_DIR/temp.json"
    fi

    # Test 3: Log file append behavior
    echo -e "\n${YELLOW}Test 3: Log file append behavior${NC}"

    # Add second entry
    tool_result=$(create_mock_tool_result "Write" "success" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Check log has 2 lines
    line_count=$(wc -l < "$log_file" | tr -d ' ')
    assert_equals "Log appended (2 entries)" "2" "$line_count"

    # Test 4: Failed tool logging
    echo -e "\n${YELLOW}Test 4: Failed tool logging${NC}"

    # Add failed entry
    tool_result=$(create_mock_tool_result "Edit" "error" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Check log has 3 lines
    line_count=$(wc -l < "$log_file" | tr -d ' ')
    assert_equals "Failed tool logged (3 entries)" "3" "$line_count"

    # Verify error status in log
    local last_line=$(tail -n 1 "$log_file")
    assert_contains "Log contains error status" "$last_line" '"status":"error"'

    # Test 5: Workflow ID tracking
    echo -e "\n${YELLOW}Test 5: Workflow ID tracking${NC}"

    # All entries should have same workflow_id
    local workflow_count=$(grep -c "\"workflow_id\":\"$workflow_id\"" "$log_file")
    assert_equals "All entries have workflow_id" "3" "$workflow_count"

    teardown_test_env
}

# ========================================
# Test Suite: view-execution-log.sh
# ========================================
test_view_execution_log() {
    echo -e "\n${BLUE}=== Testing view-execution-log.sh ===${NC}\n"

    # TODO: view-execution-log.sh not yet implemented - skip tests if missing
    if [[ ! -f "$VIEW_EXECUTION_LOG" ]]; then
        echo -e "${YELLOW}SKIPPED: view-execution-log.sh not found at $VIEW_EXECUTION_LOG${NC}"
        echo -e "${YELLOW}This component is pending implementation.${NC}"
        return 0
    fi

    setup_test_env

    # Create test log file
    local workflow_id=$(generate_test_id)
    local session_id=$(generate_test_id)
    local log_file="$TEST_LOG_DIR/execution_${workflow_id}.jsonl"

    export CLAUDE_LOG_DIR="$TEST_LOG_DIR"

    # Create sample log entries
    cat > "$log_file" <<EOF
{"tool":"Read","status":"success","session_id":"$session_id","workflow_id":"$workflow_id","timestamp":"2025-11-15T10:00:00Z","parameters":{"file_path":"/test/file1.txt"}}
{"tool":"Write","status":"success","session_id":"$session_id","workflow_id":"$workflow_id","timestamp":"2025-11-15T10:01:00Z","parameters":{"file_path":"/test/file2.txt"}}
{"tool":"Edit","status":"error","session_id":"$session_id","workflow_id":"$workflow_id","timestamp":"2025-11-15T10:02:00Z","parameters":{"file_path":"/test/file3.txt"},"error":"File not found"}
{"tool":"Bash","status":"success","session_id":"$session_id","workflow_id":"$workflow_id","timestamp":"2025-11-15T10:03:00Z","parameters":{"command":"ls -la"}}
EOF

    # Test 1: Raw output mode
    echo -e "\n${YELLOW}Test 1: Raw output mode${NC}"
    local output=$(bash "$VIEW_EXECUTION_LOG" --raw --workflow "$workflow_id" 2>/dev/null || echo "")
    assert_contains "Raw mode shows JSON" "$output" '"tool":"Read"'

    # Test 2: Formatted output mode
    echo -e "\n${YELLOW}Test 2: Formatted output mode${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" 2>/dev/null || echo "")
    assert_contains "Formatted mode shows tool name" "$output" "Read"

    # Test 3: Filter by tool
    echo -e "\n${YELLOW}Test 3: Filter by tool${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" --tool "Edit" 2>/dev/null || echo "")
    assert_contains "Filter shows Edit tool" "$output" "Edit"
    assert "Filter excludes other tools" "[[ ! '$output' =~ 'Read' ]]"

    # Test 4: Filter by status
    echo -e "\n${YELLOW}Test 4: Filter by status${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" --status "error" 2>/dev/null || echo "")
    assert_contains "Filter shows error status" "$output" "error"

    # Test 5: Filter by session
    echo -e "\n${YELLOW}Test 5: Filter by session${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" --session "$session_id" 2>/dev/null || echo "")
    line_count=$(echo "$output" | grep -c "tool" || echo "0")
    assert "Filter by session shows all entries" "[[ $line_count -ge 4 ]]"

    # Test 6: Combined filters (AND logic)
    echo -e "\n${YELLOW}Test 6: Combined filters${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" --tool "Edit" --status "error" 2>/dev/null || echo "")
    assert_contains "Combined filter shows Edit error" "$output" "Edit"
    assert_contains "Combined filter shows error" "$output" "error"

    # Test 7: Workflow view
    echo -e "\n${YELLOW}Test 7: Workflow view${NC}"
    output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" --workflow-view 2>/dev/null || echo "")
    assert_contains "Workflow view shows summary" "$output" "Workflow"

    # Test 8: No results scenario
    echo -e "\n${YELLOW}Test 8: No results scenario${NC}"
    bash "$VIEW_EXECUTION_LOG" --workflow "nonexistent_workflow" 2>/dev/null
    local exit_code=$?
    assert_equals "No results returns exit code 2" "2" "$exit_code"

    teardown_test_env
}

# ========================================
# Test Suite: End-to-End Workflow
# ========================================
test_end_to_end_workflow() {
    echo -e "\n${BLUE}=== Testing End-to-End Workflow ===${NC}\n"

    setup_test_env

    local workflow_id=$(generate_test_id)
    local session_id=$(generate_test_id)

    export CLAUDE_STATE_DIR="$TEST_STATE_DIR"
    export CLAUDE_LOG_DIR="$TEST_LOG_DIR"

    # Test 1: Multi-tool workflow with failures
    echo -e "\n${YELLOW}Test 1: Multi-tool workflow simulation${NC}"

    # Tool 1: Success
    local tool_result=$(create_mock_tool_result "Read" "success" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Tool 2: Failure (triggers retry)
    tool_result=$(create_mock_tool_result "Write" "error" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$RETRY_HANDLER" > /dev/null 2>&1 || true
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Tool 3: Success
    tool_result=$(create_mock_tool_result "Edit" "success" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Verify retry state created
    local retry_file="$TEST_STATE_DIR/retry_budgets.json"
    assert_file_exists "Retry state created for failed tool" "$retry_file"

    # Verify execution log created
    local log_file="$TEST_LOG_DIR/execution_${workflow_id}.jsonl"
    assert_file_exists "Execution log created" "$log_file"

    # Verify log has 3 entries
    local line_count=$(wc -l < "$log_file" | tr -d ' ')
    assert_equals "Log contains 3 entries" "3" "$line_count"

    # Test 2: Workflow reconstruction
    echo -e "\n${YELLOW}Test 2: Workflow reconstruction${NC}"
    if [[ -f "$VIEW_EXECUTION_LOG" ]]; then
        local output=$(bash "$VIEW_EXECUTION_LOG" --workflow "$workflow_id" 2>/dev/null || echo "")
        assert_contains "Workflow shows Read tool" "$output" "Read"
        assert_contains "Workflow shows Write tool" "$output" "Write"
        assert_contains "Workflow shows Edit tool" "$output" "Edit"
    else
        echo -e "${YELLOW}SKIPPED: view-execution-log.sh not available${NC}"
    fi

    # Test 3: Retry recovery (failed -> retry -> success)
    echo -e "\n${YELLOW}Test 3: Retry recovery${NC}"

    # Simulate retry success
    tool_result=$(create_mock_tool_result "Write" "success" "$session_id" "$workflow_id")
    echo "$tool_result" | bash "$EXECUTION_LOGGER" > /dev/null 2>&1 || true

    # Verify log now has 4 entries (including retry success)
    line_count=$(wc -l < "$log_file" | tr -d ' ')
    assert_equals "Log contains retry entry (4 total)" "4" "$line_count"

    # Verify retry state still exists (cleanup handled elsewhere)
    assert_file_exists "Retry state persists after recovery" "$retry_file"

    # Test 4: Context passing verification
    echo -e "\n${YELLOW}Test 4: Context passing through retry cycle${NC}"

    # Both Write entries (failed and retry) should have same session_id
    local write_count=$(grep -c '"tool":"Write"' "$log_file")
    assert_equals "Write tool logged twice (fail + retry)" "2" "$write_count"

    local write_session_count=$(grep '"tool":"Write"' "$log_file" | grep -c "\"session_id\":\"$session_id\"")
    assert_equals "Both Write entries have same session_id" "2" "$write_session_count"

    teardown_test_env
}

# ========================================
# Main Test Runner
# ========================================
main() {
    echo -e "${BLUE}"
    echo "========================================="
    echo "  PHASE A INTEGRATION TESTS"
    echo "========================================="
    echo -e "${NC}"

    local start_time=$(date +%s)

    # Run test suites
    test_retry_handler
    test_execution_logger
    test_view_execution_log
    test_end_to_end_workflow

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    echo -e "${BLUE}Test duration: ${duration}s${NC}"

    # Print summary and exit
    print_test_summary
}

# Run tests if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
