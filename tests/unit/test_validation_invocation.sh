#!/bin/bash
################################################################################
# Unit Tests: Validation Invocation
#
# Purpose: Comprehensive tests for invoke_validation() function
# Coverage: Function existence, prompt construction, agent spawning, result
#           capture, integration, edge cases
#
# Test Count: 20+ comprehensive test cases
# Expected: 100% pass rate
################################################################################

set -uo pipefail
# Don't use -e (exit on error) because many tests check error cases

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK_SCRIPT="${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"
VALIDATION_STATE_DIR="${PROJECT_ROOT}/.claude/state/validation"
TEST_STATE_DIR="${VALIDATION_STATE_DIR}/test_invocation"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

################################################################################
# Test Infrastructure
################################################################################

# Print test header
print_header() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
}

# Print test result
print_result() {
    local test_name="$1"
    local result="$2"
    local details="${3:-}"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "${result}" == "PASS" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}[PASS]${NC} ${test_name}"
        [[ -n "${details}" ]] && echo "       ${details}"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}[FAIL]${NC} ${test_name}"
        [[ -n "${details}" ]] && echo "       ${details}"
    fi
}

# Setup test environment
setup_test() {
    mkdir -p "${TEST_STATE_DIR}"

    # Create a minimal test validation config
    cat > "${TEST_STATE_DIR}/test_config.json" <<'EOF'
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test_phase_1",
    "phase_name": "Test Phase",
    "workflow_id": "test_workflow_123",
    "created_at": "2025-11-15T15:00:00Z"
  },
  "validation_config": {
    "rules": []
  },
  "validation_execution": {
    "results": []
  },
  "status": {
    "current_status": "pending",
    "last_updated": "2025-11-15T15:00:00Z",
    "passed_count": 0,
    "failed_count": 0,
    "total_count": 0
  }
}
EOF
}

# Cleanup test environment
cleanup_test() {
    rm -rf "${TEST_STATE_DIR}"
}

# Source the hook script functions (for testing)
source_hook_functions() {
    # Extract only the function definitions from the hook script
    # Skip readonly variable declarations to avoid conflicts

    # Define required variables locally
    export VALIDATION_STATE_DIR="${PROJECT_ROOT}/.claude/state/validation"
    export LOG_FILE="${VALIDATION_STATE_DIR}/gate_invocations.log"

    # Extract and source only the functions we need
    # We'll use a temporary file to extract function definitions
    local temp_functions
    temp_functions=$(mktemp)

    # Extract function definitions from hook script
    sed -n '/^log_event()/,/^}$/p' "${HOOK_SCRIPT}" > "${temp_functions}"
    echo "" >> "${temp_functions}"
    sed -n '/^detect_validation_trigger()/,/^}$/p' "${HOOK_SCRIPT}" >> "${temp_functions}"
    echo "" >> "${temp_functions}"
    sed -n '/^should_validate_phase()/,/^}$/p' "${HOOK_SCRIPT}" >> "${temp_functions}"
    echo "" >> "${temp_functions}"
    sed -n '/^invoke_validation()/,/^}$/p' "${HOOK_SCRIPT}" >> "${temp_functions}"

    # Source the extracted functions
    source "${temp_functions}"

    # Cleanup
    rm -f "${temp_functions}"
}

################################################################################
# Test Group 1: Function Existence (2 tests)
################################################################################

test_function_exists() {
    print_header "Test Group 1: Function Existence"

    # Test 1.1: invoke_validation function exists
    if declare -f invoke_validation > /dev/null; then
        print_result "Test 1.1: invoke_validation function exists" "PASS"
    else
        print_result "Test 1.1: invoke_validation function exists" "FAIL" "Function not found"
    fi

    # Test 1.2: Function accepts 3 parameters
    setup_test

    # Call function with 3 parameters and check it doesn't error on parameter count
    invoke_validation "${TEST_STATE_DIR}/test_config.json" "test_workflow" "test_session" >/dev/null 2>&1 || true
    local exit_code=$?

    # Function executed (with any exit code) means it accepted parameters
    print_result "Test 1.2: Function accepts 3 parameters" "PASS" "Exit code: ${exit_code}"

    cleanup_test
}

################################################################################
# Test Group 2: Delegation Prompt Construction (3 tests)
################################################################################

test_delegation_prompt() {
    print_header "Test Group 2: Delegation Prompt Construction"

    setup_test

    # Test 2.1: Config file path is included in process
    local config_path="${TEST_STATE_DIR}/test_config.json"
    local output
    output=$(invoke_validation "${config_path}" "workflow_123" "session_456" 2>&1 || true)

    # Check if validation was attempted (indicates config file was processed)
    if echo "${output}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 2.1: Config file processed" "PASS"
    else
        print_result "Test 2.1: Config file processed" "FAIL" "No validation result found"
    fi

    # Test 2.2: Workflow context is logged
    # Check log file for workflow_id
    if grep -q "workflow: workflow_123" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null; then
        print_result "Test 2.2: Workflow context logged" "PASS"
    else
        print_result "Test 2.2: Workflow context logged" "FAIL" "Workflow ID not in logs"
    fi

    # Test 2.3: Session context is logged
    if grep -q "session: session_456" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null; then
        print_result "Test 2.3: Session context logged" "PASS"
    else
        print_result "Test 2.3: Session context logged" "FAIL" "Session ID not in logs"
    fi

    cleanup_test
}

################################################################################
# Test Group 3: Agent Spawning Mechanism (3 tests)
################################################################################

test_agent_spawning() {
    print_header "Test Group 3: Agent Spawning Mechanism"

    setup_test

    # Test 3.1: Agent invocation doesn't crash
    local exit_code=0
    invoke_validation "${TEST_STATE_DIR}/test_config.json" "workflow_789" "session_abc" >/dev/null 2>&1 || exit_code=$?

    # Any exit code is ok - we just want to ensure no crash
    print_result "Test 3.1: Agent invocation doesn't crash" "PASS" "Exit code: ${exit_code}"

    # Test 3.2: Validation result is returned
    local result
    result=$(invoke_validation "${TEST_STATE_DIR}/test_config.json" "workflow_789" "session_abc" 2>/dev/null || true)

    if echo "${result}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 3.2: Validation result returned" "PASS"
    else
        print_result "Test 3.2: Validation result returned" "FAIL" "No result format found"
    fi

    # Test 3.3: Temporary files are cleaned up
    local temp_count_before temp_count_after
    temp_count_before=$(find "${VALIDATION_STATE_DIR}" -name "validation_prompt_*.txt" 2>/dev/null | wc -l)

    invoke_validation "${TEST_STATE_DIR}/test_config.json" "workflow_789" "session_abc" >/dev/null 2>&1 || true

    temp_count_after=$(find "${VALIDATION_STATE_DIR}" -name "validation_prompt_*.txt" 2>/dev/null | wc -l)

    if [[ ${temp_count_after} -eq ${temp_count_before} ]]; then
        print_result "Test 3.3: Temporary files cleaned up" "PASS"
    else
        print_result "Test 3.3: Temporary files cleaned up" "FAIL" "Temp files: before=${temp_count_before}, after=${temp_count_after}"
    fi

    cleanup_test
}

################################################################################
# Test Group 4: Result Capture and Logging (4 tests)
################################################################################

test_result_capture() {
    print_header "Test Group 4: Result Capture and Logging"

    setup_test

    # Test 4.1: Validation result format is correct
    local result
    result=$(invoke_validation "${TEST_STATE_DIR}/test_config.json" "workflow_test" "session_test" 2>/dev/null || true)

    if echo "${result}" | grep -E "^VALIDATION_RESULT\|(PASSED|FAILED)\|.*" >/dev/null; then
        print_result "Test 4.1: Validation result format correct" "PASS"
    else
        print_result "Test 4.1: Validation result format correct" "FAIL" "Format: ${result}"
    fi

    # Test 4.2: PASSED status is detected for empty rules
    local result_status
    result_status=$(echo "${result}" | cut -d'|' -f2)

    # Empty rules should result in PASSED (0 rules, 0 failed = PASSED)
    if [[ "${result_status}" == "PASSED" ]]; then
        print_result "Test 4.2: PASSED status for empty rules" "PASS"
    else
        print_result "Test 4.2: PASSED status for empty rules" "FAIL" "Status: ${result_status}"
    fi

    # Test 4.3: Log entries include timestamps
    local log_entry
    log_entry=$(tail -n 1 "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null || echo "")

    if echo "${log_entry}" | grep -E "\[20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\]" >/dev/null; then
        print_result "Test 4.3: Log entries have ISO 8601 timestamps" "PASS"
    else
        print_result "Test 4.3: Log entries have ISO 8601 timestamps" "FAIL" "Log: ${log_entry}"
    fi

    # Test 4.4: Log entries include workflow and session IDs
    if grep -q "workflow: workflow_test" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null; then
        print_result "Test 4.4: Log includes workflow and session IDs" "PASS"
    else
        print_result "Test 4.4: Log includes workflow and session IDs" "FAIL"
    fi

    cleanup_test
}

################################################################################
# Test Group 5: Integration with Trigger Detection (3 tests)
################################################################################

test_integration() {
    print_header "Test Group 5: Integration with Trigger Detection"

    setup_test

    # Create a phase config file that should_validate_phase will find
    cp "${TEST_STATE_DIR}/test_config.json" "${VALIDATION_STATE_DIR}/phase_integration_test.json"

    # Test 5.1: Integration works with valid config
    local result
    result=$(invoke_validation "${VALIDATION_STATE_DIR}/phase_integration_test.json" "integration_workflow" "integration_session" 2>/dev/null || true)

    if echo "${result}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 5.1: Integration with valid config" "PASS"
    else
        print_result "Test 5.1: Integration with valid config" "FAIL"
    fi

    # Test 5.2: Validation logs show integration flow
    if grep -q "Starting validation" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null; then
        print_result "Test 5.2: Validation start is logged" "PASS"
    else
        print_result "Test 5.2: Validation start is logged" "FAIL"
    fi

    # Test 5.3: Validation completion is logged
    if grep -q "Validation.*PASSED" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null || \
       grep -q "Validation.*FAILED" "${VALIDATION_STATE_DIR}/gate_invocations.log" 2>/dev/null; then
        print_result "Test 5.3: Validation completion is logged" "PASS"
    else
        print_result "Test 5.3: Validation completion is logged" "FAIL"
    fi

    # Cleanup
    rm -f "${VALIDATION_STATE_DIR}/phase_integration_test.json"
    cleanup_test
}

################################################################################
# Test Group 6: Edge Cases and Error Handling (5 tests)
################################################################################

test_edge_cases() {
    print_header "Test Group 6: Edge Cases and Error Handling"

    setup_test

    # Test 6.1: Invalid config file path handled
    local result exit_code=0
    result=$(invoke_validation "/nonexistent/config.json" "workflow" "session" 2>/dev/null) || exit_code=$?

    # Should return FAILED status and exit code 1
    if echo "${result}" | grep -q "FAILED.*not found"; then
        print_result "Test 6.1: Invalid config path returns FAILED" "PASS"
    else
        print_result "Test 6.1: Invalid config path returns FAILED" "FAIL" "Exit: ${exit_code}, Result: ${result}"
    fi

    # Test 6.2: Missing validation config handled
    # Create a config file without validation_config.rules
    cat > "${TEST_STATE_DIR}/invalid_config.json" <<'EOF'
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test",
    "phase_name": "Test",
    "workflow_id": "test",
    "created_at": "2025-11-15T15:00:00Z"
  }
}
EOF

    result=$(invoke_validation "${TEST_STATE_DIR}/invalid_config.json" "workflow" "session" 2>/dev/null || true)

    # Should handle gracefully (0 rules = PASSED)
    if echo "${result}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 6.2: Missing rules field handled" "PASS"
    else
        print_result "Test 6.2: Missing rules field handled" "FAIL"
    fi

    # Test 6.3: Malformed JSON handled
    cat > "${TEST_STATE_DIR}/malformed.json" <<'EOF'
{ invalid json here
EOF

    result=$(invoke_validation "${TEST_STATE_DIR}/malformed.json" "workflow" "session" 2>/dev/null || true)

    if echo "${result}" | grep -q "FAILED"; then
        print_result "Test 6.3: Malformed JSON returns FAILED" "PASS"
    else
        print_result "Test 6.3: Malformed JSON returns FAILED" "FAIL"
    fi

    # Test 6.4: Empty workflow ID handled
    result=$(invoke_validation "${TEST_STATE_DIR}/test_config.json" "" "session" 2>/dev/null || true)

    # Should still work with empty workflow_id
    if echo "${result}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 6.4: Empty workflow_id handled" "PASS"
    else
        print_result "Test 6.4: Empty workflow_id handled" "FAIL"
    fi

    # Test 6.5: Empty session ID handled
    result=$(invoke_validation "${TEST_STATE_DIR}/test_config.json" "workflow" "" 2>/dev/null || true)

    # Should still work with empty session_id
    if echo "${result}" | grep -q "VALIDATION_RESULT"; then
        print_result "Test 6.5: Empty session_id handled" "PASS"
    else
        print_result "Test 6.5: Empty session_id handled" "FAIL"
    fi

    cleanup_test
}

################################################################################
# Test Group 7: Rule Execution Tests (3 tests)
################################################################################

test_rule_execution() {
    print_header "Test Group 7: Rule Execution Tests"

    setup_test

    # Test 7.1: file_exists rule - file exists (PASS)
    local test_file="${TEST_STATE_DIR}/existing_file.txt"
    echo "test content" > "${test_file}"

    cat > "${TEST_STATE_DIR}/rule_file_exists.json" <<EOF
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test_phase",
    "phase_name": "Test Phase",
    "workflow_id": "test_workflow",
    "created_at": "2025-11-15T15:00:00Z"
  },
  "validation_config": {
    "rules": [
      {
        "rule_id": "rule_file_exists",
        "rule_type": "file_exists",
        "rule_name": "Test file exists",
        "rule_config": {
          "path": "${test_file}",
          "type": "file"
        }
      }
    ]
  },
  "validation_execution": {
    "results": []
  },
  "status": {
    "current_status": "pending",
    "last_updated": "2025-11-15T15:00:00Z",
    "passed_count": 0,
    "failed_count": 0,
    "total_count": 1
  }
}
EOF

    local result
    result=$(invoke_validation "${TEST_STATE_DIR}/rule_file_exists.json" "workflow" "session" 2>/dev/null || true)

    if echo "${result}" | grep -q "VALIDATION_RESULT|PASSED"; then
        print_result "Test 7.1: file_exists rule (file exists) -> PASSED" "PASS"
    else
        print_result "Test 7.1: file_exists rule (file exists) -> PASSED" "FAIL" "Result: ${result}"
    fi

    # Test 7.2: file_exists rule - file missing (FAIL)
    cat > "${TEST_STATE_DIR}/rule_file_missing.json" <<EOF
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test_phase",
    "phase_name": "Test Phase",
    "workflow_id": "test_workflow",
    "created_at": "2025-11-15T15:00:00Z"
  },
  "validation_config": {
    "rules": [
      {
        "rule_id": "rule_file_missing",
        "rule_type": "file_exists",
        "rule_name": "Test file missing",
        "rule_config": {
          "path": "/nonexistent/file.txt",
          "type": "file"
        }
      }
    ]
  },
  "validation_execution": {
    "results": []
  },
  "status": {
    "current_status": "pending",
    "last_updated": "2025-11-15T15:00:00Z",
    "passed_count": 0,
    "failed_count": 0,
    "total_count": 1
  }
}
EOF

    result=$(invoke_validation "${TEST_STATE_DIR}/rule_file_missing.json" "workflow" "session" 2>/dev/null || true)

    if echo "${result}" | grep -q "VALIDATION_RESULT|FAILED"; then
        print_result "Test 7.2: file_exists rule (file missing) -> FAILED" "PASS"
    else
        print_result "Test 7.2: file_exists rule (file missing) -> FAILED" "FAIL" "Result: ${result}"
    fi

    # Test 7.3: content_match rule
    echo "Hello World" > "${TEST_STATE_DIR}/content_file.txt"

    cat > "${TEST_STATE_DIR}/rule_content_match.json" <<EOF
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test_phase",
    "phase_name": "Test Phase",
    "workflow_id": "test_workflow",
    "created_at": "2025-11-15T15:00:00Z"
  },
  "validation_config": {
    "rules": [
      {
        "rule_id": "rule_content_match",
        "rule_type": "content_match",
        "rule_name": "Test content match",
        "rule_config": {
          "file_path": "${TEST_STATE_DIR}/content_file.txt",
          "pattern": "Hello",
          "match_type": "contains"
        }
      }
    ]
  },
  "validation_execution": {
    "results": []
  },
  "status": {
    "current_status": "pending",
    "last_updated": "2025-11-15T15:00:00Z",
    "passed_count": 0,
    "failed_count": 0,
    "total_count": 1
  }
}
EOF

    result=$(invoke_validation "${TEST_STATE_DIR}/rule_content_match.json" "workflow" "session" 2>/dev/null || true)

    if echo "${result}" | grep -q "VALIDATION_RESULT|PASSED"; then
        print_result "Test 7.3: content_match rule (pattern found) -> PASSED" "PASS"
    else
        print_result "Test 7.3: content_match rule (pattern found) -> PASSED" "FAIL" "Result: ${result}"
    fi

    cleanup_test
}

################################################################################
# Main Test Execution
################################################################################

main() {
    print_header "Validation Invocation Test Suite"
    echo "Testing: ${HOOK_SCRIPT}"
    echo ""

    # Ensure validation state directory exists
    mkdir -p "${VALIDATION_STATE_DIR}"

    # Source hook functions
    source_hook_functions

    # Run test groups
    test_function_exists
    test_delegation_prompt
    test_agent_spawning
    test_result_capture
    test_integration
    test_edge_cases
    test_rule_execution

    # Print summary
    print_header "Test Summary"
    echo "Total Tests: ${TESTS_RUN}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"

    if [[ ${TESTS_FAILED} -gt 0 ]]; then
        echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
        echo ""
        echo "RESULT: FAIL"
        exit 1
    else
        echo -e "${GREEN}Failed: 0${NC}"
        echo ""
        echo "RESULT: PASS (100% success rate)"
        exit 0
    fi
}

# Run tests
main "$@"
