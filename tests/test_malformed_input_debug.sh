#!/bin/bash
################################################################################
# Test: Malformed Input Debug Logging
#
# Purpose: Verify that validation_gate.sh captures malformed JSON input
# Tests:
#   1. Missing 'tool' object
#   2. Missing 'tool.name' field
#   3. Valid input with tool.name
#   4. Input truncation for large JSON
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOOK_SCRIPT="${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"
LOG_FILE="${PROJECT_ROOT}/.claude/state/validation/gate_invocations.log"
TEST_LOG_FILE="${PROJECT_ROOT}/.claude/state/validation/test_malformed_debug_$(date +%s).log"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper: Print test header
print_test_header() {
    echo ""
    echo "=========================================="
    echo "TEST: $1"
    echo "=========================================="
}

# Helper: Print test result
print_result() {
    local status="$1"
    local message="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "${status}" == "PASS" ]]; then
        echo -e "${GREEN}✓ PASS${NC}: ${message}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: ${message}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Helper: Clear log file
clear_log() {
    mkdir -p "$(dirname "${LOG_FILE}")"
    > "${LOG_FILE}"
}

# Helper: Check log for pattern
check_log() {
    local pattern="$1"
    local description="$2"

    if grep -q "${pattern}" "${LOG_FILE}"; then
        print_result "PASS" "${description}"
        return 0
    else
        print_result "FAIL" "${description} (pattern not found: ${pattern})"
        echo "Last 10 log lines:"
        tail -10 "${LOG_FILE}"
        return 1
    fi
}

################################################################################
# TEST 1: Missing 'tool' object
################################################################################
print_test_header "Test 1: Missing 'tool' object"

clear_log

# Create malformed JSON: missing 'tool' object
MALFORMED_JSON='{"sessionId":"test_session_001","workflowId":"test_workflow_001","timestamp":"2025-11-17T20:00:00Z"}'

echo "Input JSON: ${MALFORMED_JSON}"
echo "${MALFORMED_JSON}" | bash "${HOOK_SCRIPT}" >/dev/null 2>&1 || true

# Check log contains error about missing 'tool' object
check_log "Missing 'tool' object in hook input" "Logs missing 'tool' object error"

# Check log contains available fields
check_log "Available fields:" "Logs available fields for diagnosis"

# Check log contains raw input
check_log "sessionId" "Logs raw input for malformed JSON"

################################################################################
# TEST 2: Missing 'tool.name' field
################################################################################
print_test_header "Test 2: Missing 'tool.name' field"

clear_log

# Create malformed JSON: 'tool' object exists but missing 'name' field
MALFORMED_JSON='{"sessionId":"test_session_002","workflowId":"test_workflow_002","tool":{"result":"test result","parameters":{"prompt":"test"}}}'

echo "Input JSON: ${MALFORMED_JSON}"
echo "${MALFORMED_JSON}" | bash "${HOOK_SCRIPT}" >/dev/null 2>&1 || true

# Check log contains error about missing 'tool.name' field
check_log "Missing 'tool.name' field" "Logs missing 'tool.name' field error"

# Check log contains available tool fields
check_log "Available tool fields:" "Logs available tool fields for diagnosis"

# Check log contains tool object
check_log '"result"' "Logs tool object structure"

################################################################################
# TEST 3: Valid input with tool.name
################################################################################
print_test_header "Test 3: Valid input with tool.name"

clear_log

# Create valid JSON
VALID_JSON='{"sessionId":"test_session_003","workflowId":"test_workflow_003","tool":{"name":"Task","parameters":{"prompt":"test task"},"result":"test result"}}'

echo "Input JSON: ${VALID_JSON}"
echo "${VALID_JSON}" | bash "${HOOK_SCRIPT}" >/dev/null 2>&1 || true

# Check log contains debug input capture
check_log "\\[DEBUG\\] \\[hook_input\\]" "Captures raw input in DEBUG log"

# Check log contains input length
check_log "length: ${#VALID_JSON}" "Logs input length for valid JSON"

# Verify no malformed errors
if grep -q "malformed_input" "${LOG_FILE}"; then
    print_result "FAIL" "Should not log malformed_input error for valid JSON"
else
    print_result "PASS" "No malformed_input error for valid JSON"
fi

################################################################################
# TEST 4: Input truncation for large JSON
################################################################################
print_test_header "Test 4: Input truncation for large JSON"

clear_log

# Create large JSON (>500 chars)
LARGE_TOOL_RESULT='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. More text to exceed 500 chars. Even more text. And more. And more.'
LARGE_JSON='{"sessionId":"test_session_004","workflowId":"test_workflow_004","tool":{"name":"Task","parameters":{"prompt":"test"},"result":"'"${LARGE_TOOL_RESULT}"'"}}'

echo "Input JSON length: ${#LARGE_JSON}"
echo "${LARGE_JSON}" | bash "${HOOK_SCRIPT}" >/dev/null 2>&1 || true

# Check log contains truncation notice
check_log "\\[truncated from" "Logs truncation notice for large input"

# Verify truncation to 500 chars
if grep -q "length: ${#LARGE_JSON}" "${LOG_FILE}"; then
    print_result "PASS" "Logs full input length before truncation"
else
    print_result "FAIL" "Should log full input length"
fi

################################################################################
# TEST 5: Tool object exists but empty
################################################################################
print_test_header "Test 5: Tool object exists but is empty"

clear_log

# Create malformed JSON: empty 'tool' object
MALFORMED_JSON='{"sessionId":"test_session_005","workflowId":"test_workflow_005","tool":{}}'

echo "Input JSON: ${MALFORMED_JSON}"
echo "${MALFORMED_JSON}" | bash "${HOOK_SCRIPT}" >/dev/null 2>&1 || true

# Check log contains error about missing 'tool.name'
check_log "Missing 'tool.name' field" "Logs missing 'tool.name' for empty tool object"

# Check log shows empty tool fields
check_log "Available tool fields:" "Logs available tool fields (empty)"

################################################################################
# TEST SUMMARY
################################################################################
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo "Tests Run:    ${TESTS_RUN}"
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [[ ${TESTS_FAILED} -eq 0 ]]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
