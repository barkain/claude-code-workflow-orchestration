#!/usr/bin/env bash

################################################################################
# Test: PostToolUse Hook Blocking Integration
#
# Purpose: Verify that the hook correctly blocks execution when validation fails
#
# Test Scenarios:
# 1. PASSED validation → Hook exits 0 (allow)
# 2. FAILED validation → Hook exits 1 (block)
# 3. UNKNOWN validation → Hook exits 0 (fail-open)
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

setup_test_state() {
    local workflow_id="$1"
    local phase_id="$2"
    local validation_status="$3"

    # Create validation state file with correct naming: phase_{workflow_id}_{phase_id}_validation.json
    local state_file="${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    cat > "${state_file}" <<EOF
{
  "workflow_id": "${workflow_id}",
  "phase_id": "${phase_id}",
  "session_id": "test_session_123",
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

setup_test_config() {
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
  "validation_rules": []
}
EOF
    echo "${config_file}"
}

create_hook_stdin() {
    local tool_name="$1"
    local session_id="$2"
    local workflow_id="${3:-test_workflow_001}"

    # Simulate TaskExecute hook stdin with workflow_id in result
    cat <<EOF
{
  "hook": {
    "type": "PostToolUse",
    "matcher": "*"
  },
  "tool": {
    "name": "${tool_name}",
    "params": {
      "task": "Test task"
    }
  },
  "result": {
    "workflow_id": "${workflow_id}"
  },
  "sessionId": "${session_id}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

################################################################################
# Test Cases
################################################################################

test_passed_validation() {
    log_test "Test 1: PASSED validation should allow (exit 0)"

    local workflow_id="test_workflow_001"
    local phase_id="phase_1"
    local session_id="test_session_123"

    # Setup test files
    setup_test_state "${workflow_id}" "${phase_id}" "PASSED"
    setup_test_config "${workflow_id}" "${phase_id}"

    # Run hook with simulated stdin
    local exit_code=0
    create_hook_stdin "Task" "${session_id}" "${workflow_id}" | bash "${HOOK_SCRIPT}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "Hook exited with code 0 (allow) for PASSED validation"
    else
        log_fail "Hook exited with code ${exit_code}, expected 0"
    fi

    # Cleanup
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}.json"
}

test_failed_validation() {
    log_test "Test 2: FAILED validation should block (exit 1)"

    local workflow_id="test_workflow_002"
    local phase_id="phase_2"
    local session_id="test_session_456"

    # Setup test files
    setup_test_state "${workflow_id}" "${phase_id}" "FAILED"
    setup_test_config "${workflow_id}" "${phase_id}"

    # Run hook with simulated stdin
    local exit_code=0
    create_hook_stdin "Task" "${session_id}" "${workflow_id}" | bash "${HOOK_SCRIPT}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 1 ]]; then
        log_pass "Hook exited with code 1 (block) for FAILED validation"
    else
        log_fail "Hook exited with code ${exit_code}, expected 1"
    fi

    # Cleanup
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}.json"
}

test_unknown_validation() {
    log_test "Test 3: UNKNOWN validation should allow (exit 0, fail-open)"

    local workflow_id="test_workflow_003"
    local phase_id="phase_3"
    local session_id="test_session_789"

    # Setup test files
    setup_test_state "${workflow_id}" "${phase_id}" "UNKNOWN"
    setup_test_config "${workflow_id}" "${phase_id}"

    # Run hook with simulated stdin
    local exit_code=0
    create_hook_stdin "Task" "${session_id}" "${workflow_id}" | bash "${HOOK_SCRIPT}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "Hook exited with code 0 (allow, fail-open) for UNKNOWN validation"
    else
        log_fail "Hook exited with code ${exit_code}, expected 0"
    fi

    # Cleanup
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}_validation.json"
    rm -f "${TEST_STATE_DIR}/phase_${workflow_id}_${phase_id}.json"
}

test_non_delegation_tool() {
    log_test "Test 4: Non-delegation tool should skip validation (exit 0)"

    # Run hook with non-delegation tool (e.g., Read)
    local exit_code=0
    create_hook_stdin "Read" "session_skip_001" | bash "${HOOK_SCRIPT}" || exit_code=$?

    # Verify exit code
    if [[ ${exit_code} -eq 0 ]]; then
        log_pass "Hook exited with code 0 (skip) for non-delegation tool"
    else
        log_fail "Hook exited with code ${exit_code}, expected 0"
    fi
}

################################################################################
# Main Test Execution
################################################################################

main() {
    echo ""
    echo "======================================"
    echo "PostToolUse Hook Blocking Integration"
    echo "======================================"
    echo ""

    # Run all test cases
    test_passed_validation
    test_failed_validation
    test_unknown_validation
    test_non_delegation_tool

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
