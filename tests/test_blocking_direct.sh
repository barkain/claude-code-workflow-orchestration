#!/usr/bin/env bash

################################################################################
# Test: Blocking Integration - Direct Test
#
# Purpose: Test blocking behavior by checking hook exit codes
#
# Test Scenarios:
# 1. PASSED validation state exists → Hook allows (exit 0)
# 2. FAILED validation state exists → Hook blocks (exit 1)
# 3. No validation state → Hook allows (exit 0, fail-open)
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

# Hook script path
HOOK_SCRIPT="${PROJECT_DIR}/hooks/PostToolUse/validation_gate.sh"

# Test state directory
TEST_STATE_DIR="${PROJECT_DIR}/.claude/state/validation"
mkdir -p "${TEST_STATE_DIR}"

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

log_info() {
    echo -e "  [INFO] $*"
}

setup_validation_state() {
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
}

setup_phase_config() {
    local workflow_id="$1"
    local phase_id="$2"

    # Create phase config file
    local config_file="${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}.json"
    cat > "${config_file}" <<EOF
{
  "version": "1.0",
  "metadata": {
    "phase_id": "${phase_id}",
    "workflow_id": "${workflow_id}",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  },
  "validation_rules": [
    {
      "rule_id": "test_rule_1",
      "rule_type": "content_match",
      "description": "Test rule",
      "pattern": "test",
      "blocking": true
    }
  ]
}
EOF
}

call_evaluate_blocking_rules() {
    local workflow_id="$1"
    local phase_id="$2"

    # Call evaluate_blocking_rules function by sourcing and calling it
    bash -c "
        source '${HOOK_SCRIPT}' 2>/dev/null
        evaluate_blocking_rules '${workflow_id}' '${phase_id}'
    "
}

cleanup_test_files() {
    local workflow_id="$1"
    local phase_id="$2"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}.json"
}

################################################################################
# Test Cases
################################################################################

test_passed_validation_allows() {
    log_test "Test 1: PASSED validation state → evaluate_blocking_rules returns 0"

    local workflow_id="wf_test_pass"
    local phase_id="phase_pass"

    # Setup validation state
    setup_validation_state "${workflow_id}" "${phase_id}" "PASSED"
    log_info "Created PASSED validation state"

    # Call function and capture exit code
    local exit_code=0
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "PASSED validation → allow (exit 0)"
    else
        log_fail "Got exit code ${exit_code}, expected 0"
    fi

    # Cleanup
    cleanup_test_files "${workflow_id}" "${phase_id}"
}

test_failed_validation_blocks() {
    log_test "Test 2: FAILED validation state → evaluate_blocking_rules returns 1"

    local workflow_id="wf_test_fail"
    local phase_id="phase_fail"

    # Setup validation state
    setup_validation_state "${workflow_id}" "${phase_id}" "FAILED"
    log_info "Created FAILED validation state"

    # Call function and capture exit code
    local exit_code=0
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify
    if [[ ${exit_code} -eq 1 ]]; then
        log_pass "FAILED validation → block (exit 1)"
    else
        log_fail "Got exit code ${exit_code}, expected 1"
    fi

    # Cleanup
    cleanup_test_files "${workflow_id}" "${phase_id}"
}

test_unknown_validation_allows() {
    log_test "Test 3: No validation state (UNKNOWN) → evaluate_blocking_rules returns 0"

    local workflow_id="wf_test_unknown"
    local phase_id="phase_unknown"

    # Don't create validation state file (will be UNKNOWN)
    log_info "No validation state file (UNKNOWN)"

    # Call function and capture exit code
    local exit_code=0
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit_code=$?

    # Verify
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "UNKNOWN validation → allow/fail-open (exit 0)"
    else
        log_fail "Got exit code ${exit_code}, expected 0"
    fi

    # Cleanup (nothing to clean)
}

test_idempotent_calls() {
    log_test "Test 4: Multiple calls should return consistent results"

    local workflow_id="wf_test_idempotent"
    local phase_id="phase_idempotent"

    # Setup FAILED validation state
    setup_validation_state "${workflow_id}" "${phase_id}" "FAILED"
    log_info "Created FAILED validation state for idempotency test"

    # Call multiple times
    local exit1=0 exit2=0 exit3=0
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit1=$?
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit2=$?
    call_evaluate_blocking_rules "${workflow_id}" "${phase_id}" || exit3=$?

    # Verify all calls return 1
    if [[ ${exit1} -eq 1 && ${exit2} -eq 1 && ${exit3} -eq 1 ]]; then
        log_pass "Multiple calls returned consistent exit code 1"
    else
        log_fail "Inconsistent exit codes: ${exit1}, ${exit2}, ${exit3}"
    fi

    # Cleanup
    cleanup_test_files "${workflow_id}" "${phase_id}"
}

################################################################################
# Main Test Execution
################################################################################

main() {
    echo ""
    echo "================================================"
    echo "PostToolUse Hook Blocking Integration Test"
    echo "================================================"
    echo ""

    # Run all tests
    test_passed_validation_allows
    test_failed_validation_blocks
    test_unknown_validation_allows
    test_idempotent_calls

    # Print summary
    echo ""
    echo "================================================"
    echo "Test Summary"
    echo "================================================"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    echo ""

    # Exit with appropriate code
    if [[ ${TESTS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed!${NC}"
        exit 1
    fi
}

main "$@"
