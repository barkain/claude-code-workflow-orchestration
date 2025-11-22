#!/usr/bin/env bash

################################################################################
# Test: PostToolUse Hook Blocking Logic (Unit Test)
#
# Purpose: Test evaluate_blocking_rules function directly
#
# Test Scenarios:
# 1. PASSED validation → Returns 0 (allow)
# 2. FAILED validation → Returns 1 (block)
# 3. UNKNOWN validation → Returns 0 (fail-open)
################################################################################

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Test state directory
TEST_STATE_DIR="${PROJECT_DIR}/.claude/state/validation"
mkdir -p "${TEST_STATE_DIR}"

# Source the hook script functions
source "${PROJECT_DIR}/hooks/PostToolUse/validation_gate.sh"

################################################################################
# Helper Functions
################################################################################

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $*"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $*"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $*"
    ((TESTS_FAILED++))
}

setup_test_state() {
    local workflow_id="$1"
    local phase_id="$2"
    local validation_status="$3"

    # Create validation state file
    local state_file="${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    cat > "${state_file}" <<EOF
{
  "workflow_id": "${workflow_id}",
  "phase_id": "${phase_id}",
  "session_id": "test_session",
  "validation_status": "${validation_status}",
  "validated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "summary": {
    "total_rules": 5,
    "passed_rules": $([ "${validation_status}" = "PASSED" ] && echo 5 || echo 2),
    "failed_rules": $([ "${validation_status}" = "PASSED" ] && echo 0 || echo 3)
  },
  "rule_results": []
}
EOF
    echo "${state_file}"
}

cleanup_test_state() {
    local workflow_id="$1"
    local phase_id="$2"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
}

################################################################################
# Test Cases
################################################################################

test_passed_validation() {
    log_test "Test 1: PASSED validation should return 0 (allow)"

    local workflow_id="test_wf_pass"
    local phase_id="phase_pass"

    # Setup test state
    setup_test_state "${workflow_id}" "${phase_id}" "PASSED"

    # Call evaluate_blocking_rules
    local exit_code=0
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "evaluate_blocking_rules returned 0 (allow) for PASSED"
    else
        log_fail "evaluate_blocking_rules returned ${exit_code}, expected 0"
    fi

    # Cleanup
    cleanup_test_state "${workflow_id}" "${phase_id}"
}

test_failed_validation() {
    log_test "Test 2: FAILED validation should return 1 (block)"

    local workflow_id="test_wf_fail"
    local phase_id="phase_fail"

    # Setup test state
    setup_test_state "${workflow_id}" "${phase_id}" "FAILED"

    # Call evaluate_blocking_rules
    local exit_code=0
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 1 ]]; then
        log_pass "evaluate_blocking_rules returned 1 (block) for FAILED"
    else
        log_fail "evaluate_blocking_rules returned ${exit_code}, expected 1"
    fi

    # Cleanup
    cleanup_test_state "${workflow_id}" "${phase_id}"
}

test_unknown_validation() {
    log_test "Test 3: UNKNOWN validation should return 0 (fail-open)"

    local workflow_id="test_wf_unknown"
    local phase_id="phase_unknown"

    # Don't create state file - this will result in UNKNOWN status

    # Call evaluate_blocking_rules
    local exit_code=0
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "evaluate_blocking_rules returned 0 (fail-open) for UNKNOWN"
    else
        log_fail "evaluate_blocking_rules returned ${exit_code}, expected 0"
    fi
}

test_idempotent_blocking() {
    log_test "Test 4: Multiple calls should be idempotent"

    local workflow_id="test_wf_idempotent"
    local phase_id="phase_idempotent"

    # Setup test state
    setup_test_state "${workflow_id}" "${phase_id}" "FAILED"

    # Call evaluate_blocking_rules multiple times
    local exit_code1=0 exit_code2=0 exit_code3=0
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code1=$?
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code2=$?
    evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code3=$?

    # Verify all calls return same exit code
    if [[ ${exit_code1} -eq 1 && ${exit_code2} -eq 1 && ${exit_code3} -eq 1 ]]; then
        log_pass "Multiple calls returned consistent exit code (1)"
    else
        log_fail "Exit codes inconsistent: ${exit_code1}, ${exit_code2}, ${exit_code3}"
    fi

    # Cleanup
    cleanup_test_state "${workflow_id}" "${phase_id}"
}

################################################################################
# Main Test Execution
################################################################################

main() {
    echo ""
    echo "======================================"
    echo "PostToolUse Blocking Logic Unit Test"
    echo "======================================"
    echo ""

    # Run all test cases
    test_passed_validation
    test_failed_validation
    test_unknown_validation
    test_idempotent_blocking

    # Print summary
    echo ""
    echo "======================================"
    echo "Test Summary"
    echo "======================================"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    echo ""

    # Exit with appropriate code
    if [[ ${TESTS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

main "$@"
