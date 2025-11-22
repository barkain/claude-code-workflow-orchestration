#!/bin/bash
################################################################################
# Unit Test: Validation Gate Skeleton Hook
#
# Purpose: Verify validation_gate.sh skeleton implementation
# Tests:
#   1. Script is executable
#   2. Proper exit code 0 (non-blocking)
#   3. Log file creation works
#   4. Placeholder functions are defined
#   5. Trigger detection works
#   6. Log format is correct
#
# Usage: ./test_validation_gate_skeleton.sh
# Exit Code: 0 if all tests pass, 1 otherwise
################################################################################

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Test configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly HOOK_SCRIPT="${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"
readonly LOG_FILE="${PROJECT_ROOT}/.claude/state/validation/gate_invocations.log"
readonly TEST_LOG_FILE="${PROJECT_ROOT}/.claude/state/validation/test_invocations.log"

# Test state
TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# Test Helper Functions
################################################################################

# Print test header
print_header() {
    echo ""
    echo "========================================================================"
    echo "Validation Gate Skeleton Hook - Unit Tests"
    echo "========================================================================"
    echo ""
}

# Print test result
# Args:
#   $1: Test name
#   $2: Result (PASS or FAIL)
#   $3: Optional details
print_result() {
    local test_name="$1"
    local result="$2"
    local details="${3:-}"

    if [[ "${result}" == "PASS" ]]; then
        echo -e "${GREEN}✓ PASS${NC}: ${test_name}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: ${test_name}"
        if [[ -n "${details}" ]]; then
            echo -e "  ${YELLOW}Details:${NC} ${details}"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Print test summary
print_summary() {
    echo ""
    echo "========================================================================"
    echo "Test Summary"
    echo "========================================================================"
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""

    if [[ ${TESTS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    fi
}

################################################################################
# Test Cases
################################################################################

# Test 1: Verify script is executable
test_script_executable() {
    if [[ -x "${HOOK_SCRIPT}" ]]; then
        print_result "Script is executable" "PASS"
    else
        print_result "Script is executable" "FAIL" "File not executable: ${HOOK_SCRIPT}"
    fi
}

# Test 2: Verify proper exit code 0
test_exit_code() {
    local test_input='{"tool": "Task", "parameters": {"prompt": "test task"}}'
    local exit_code

    # Clear log file before test
    rm -f "${TEST_LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1 || exit_code=$?
    exit_code=${exit_code:-0}

    if [[ ${exit_code} -eq 0 ]]; then
        print_result "Exit code is 0 (non-blocking)" "PASS"
    else
        print_result "Exit code is 0 (non-blocking)" "FAIL" "Exit code: ${exit_code}"
    fi
}

# Test 3: Verify log file creation works
test_log_file_creation() {
    local test_input='{"tool": "SlashCommand", "parameters": {"command": "/test"}}'

    # Clear log file before test
    rm -f "${LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1

    if [[ -f "${LOG_FILE}" ]]; then
        print_result "Log file creation works" "PASS"
    else
        print_result "Log file creation works" "FAIL" "Log file not created: ${LOG_FILE}"
    fi
}

# Test 4: Verify placeholder functions are defined
test_placeholder_functions() {
    local functions=("detect_validation_trigger" "should_validate_phase" "invoke_validation")
    local all_defined=true
    local missing_functions=()

    for func in "${functions[@]}"; do
        if ! grep -q "^${func}()" "${HOOK_SCRIPT}"; then
            all_defined=false
            missing_functions+=("${func}")
        fi
    done

    if ${all_defined}; then
        print_result "Placeholder functions are defined" "PASS"
    else
        print_result "Placeholder functions are defined" "FAIL" "Missing: ${missing_functions[*]}"
    fi
}

# Test 5: Verify implementation is complete (no TODOs)
test_todo_comments() {
    local todo_count
    todo_count=$(grep -c "# TODO:" "${HOOK_SCRIPT}" || echo "0")

    if [[ ${todo_count} -eq 0 ]]; then
        print_result "No TODO comments (implementation complete)" "PASS"
    else
        print_result "No TODO comments (implementation complete)" "FAIL" "Found ${todo_count} TODO comments (expected 0 for completed implementation)"
    fi
}

# Test 6: Verify trigger detection for SlashCommand
test_trigger_detection_slash() {
    local test_input='{"tool": "SlashCommand", "parameters": {"command": "/delegate"}}'

    # Clear log file before test
    rm -f "${LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1

    # Check if validation trigger was detected in log
    if grep -q "\[TRIGGER\].*\[SlashCommand\].*Validation trigger detected" "${LOG_FILE}"; then
        print_result "Trigger detection for SlashCommand" "PASS"
    else
        print_result "Trigger detection for SlashCommand" "FAIL" "Trigger not detected in log"
    fi
}

# Test 7: Verify trigger detection for Task
test_trigger_detection_task() {
    local test_input='{"tool": "Task", "parameters": {"prompt": "test task"}}'

    # Clear log file before test
    rm -f "${LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1

    # Check if validation trigger was detected in log
    if grep -q "\[TRIGGER\].*\[Task\].*Validation trigger detected" "${LOG_FILE}"; then
        print_result "Trigger detection for Task" "PASS"
    else
        print_result "Trigger detection for Task" "FAIL" "Trigger not detected in log"
    fi
}

# Test 8: Verify no trigger for non-delegation tools
test_no_trigger_for_read() {
    local test_input='{"tool": "Read", "parameters": {"file_path": "/tmp/test.txt"}}'

    # Clear log file before test
    rm -f "${LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1

    # Check that validation trigger was NOT detected
    if grep -q "\[SKIP\].*\[Read\].*No validation trigger" "${LOG_FILE}"; then
        print_result "No trigger for non-delegation tools (Read)" "PASS"
    else
        print_result "No trigger for non-delegation tools (Read)" "FAIL" "Unexpected trigger detected"
    fi
}

# Test 9: Verify log format (ISO 8601 timestamp)
test_log_format() {
    local test_input='{"tool": "Task", "parameters": {"prompt": "format test"}}'

    # Clear log file before test
    rm -f "${LOG_FILE}"

    # Run hook with test input
    echo "${test_input}" | "${HOOK_SCRIPT}" > /dev/null 2>&1

    # Check log format: [YYYY-MM-DDTHH:MM:SSZ] [EVENT_TYPE] [TOOL_NAME] [DETAILS]
    if grep -Eq '^\[20[0-9]{2}-[0-1][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z\] \[[A-Z]+\] \[[A-Za-z]+\]' "${LOG_FILE}"; then
        print_result "Log format is correct (ISO 8601)" "PASS"
    else
        print_result "Log format is correct (ISO 8601)" "FAIL" "Invalid log format"
    fi
}

# Test 10: Verify script has proper shebang
test_shebang() {
    local shebang
    shebang=$(head -n 1 "${HOOK_SCRIPT}")

    if [[ "${shebang}" == "#!/bin/bash" ]]; then
        print_result "Script has proper shebang" "PASS"
    else
        print_result "Script has proper shebang" "FAIL" "Shebang: ${shebang}"
    fi
}

################################################################################
# Main Test Execution
################################################################################

main() {
    print_header

    # Run all tests
    test_script_executable
    test_shebang
    test_exit_code
    test_log_file_creation
    test_placeholder_functions
    test_todo_comments
    test_trigger_detection_slash
    test_trigger_detection_task
    test_no_trigger_for_read
    test_log_format

    # Print summary and exit
    print_summary
}

# Execute tests
main "$@"
