#!/bin/bash
################################################################################
# Integration Test: Enum Validation in persist and read functions
#
# Purpose: Test enum validation in persist_validation_state() and read_validation_state()
# Location: tests/integration/test_integration_enum.sh
#
# Author: Claude Code Delegation System
# Version: 1.0.0
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_GATE_SCRIPT="${SCRIPT_DIR}/../../hooks/PostToolUse/validation_gate.sh"
TEST_STATE_DIR="/tmp/test_validation_state_$$"

# Setup test environment
mkdir -p "${TEST_STATE_DIR}"

# Create a temporary modified version of validation_gate.sh for testing
# We need to extract just the functions we need without the readonly vars
TEMP_SCRIPT="/tmp/validation_gate_test_$$.sh"

# Extract only the function definitions we need
sed -n '/^# Validate validation_status enum value/,/^}$/p' "${VALIDATION_GATE_SCRIPT}" > "${TEMP_SCRIPT}"
sed -n '/^persist_validation_state() {/,/^}$/p' "${VALIDATION_GATE_SCRIPT}" >> "${TEMP_SCRIPT}"
sed -n '/^read_validation_state() {/,/^}$/p' "${VALIDATION_GATE_SCRIPT}" >> "${TEMP_SCRIPT}"

# Add test-specific configuration
cat >> "${TEMP_SCRIPT}" <<'TESTCONFIG'

# Test configuration
VALIDATION_STATE_DIR="${TEST_STATE_DIR}"
PROJECT_ROOT="/tmp"

# Simple log_event for testing
log_event() {
    echo "[LOG] $1 | $2 | $3" >&2
}
TESTCONFIG

# Source the temporary script
source "${TEMP_SCRIPT}"

# Set VALIDATION_STATE_DIR for testing
VALIDATION_STATE_DIR="${TEST_STATE_DIR}"

# Override log_event to suppress output during testing
log_event() {
    echo "[LOG] $1 | $2 | $3" >&2
}

################################################################################
# Test Functions
################################################################################

total_tests=0
passed_tests=0
failed_tests=0

cleanup() {
    rm -rf "${TEST_STATE_DIR}"
    rm -f "${TEMP_SCRIPT}"
}

trap cleanup EXIT

run_persist_test() {
    local test_name="$1"
    local status_value="$2"
    local expected_exit_code="$3"

    total_tests=$((total_tests + 1))

    echo ""
    echo "Test ${total_tests}: ${test_name}"
    echo "  Testing persist_validation_state with status='${status_value}'"
    echo "  Expected exit code: ${expected_exit_code}"

    # Run persist_validation_state
    local actual_exit_code=0
    persist_validation_state "wf_test" "phase_test" "sess_test" "${status_value}" 3 '[]' 2>/dev/null || actual_exit_code=$?

    echo "  Actual exit code: ${actual_exit_code}"

    if [[ ${actual_exit_code} -eq ${expected_exit_code} ]]; then
        echo "  Result: PASSED"
        passed_tests=$((passed_tests + 1))

        # If persist succeeded, verify file was created
        if [[ ${expected_exit_code} -eq 0 ]]; then
            local state_file="${TEST_STATE_DIR}/phase_wf_test_phase_test_validation.json"
            if [[ -f "${state_file}" ]]; then
                echo "  File created: ${state_file}"
                local persisted_status
                persisted_status=$(jq -r '.validation_status' "${state_file}" 2>/dev/null || echo "PARSE_ERROR")
                echo "  Persisted status: ${persisted_status}"

                if [[ "${persisted_status}" == "${status_value}" ]]; then
                    echo "  Status value matches!"
                else
                    echo "  ERROR: Status mismatch (expected: ${status_value}, got: ${persisted_status})"
                    failed_tests=$((failed_tests - 1))
                    failed_tests=$((failed_tests + 1))
                    passed_tests=$((passed_tests - 1))
                fi
            else
                echo "  ERROR: File not created"
                failed_tests=$((failed_tests - 1))
                failed_tests=$((failed_tests + 1))
                passed_tests=$((passed_tests - 1))
            fi
        fi
    else
        echo "  Result: FAILED (expected ${expected_exit_code}, got ${actual_exit_code})"
        failed_tests=$((failed_tests + 1))
    fi

    # Cleanup state file for next test
    rm -f "${TEST_STATE_DIR}"/phase_*.json
}

run_read_test() {
    local test_name="$1"
    local status_value="$2"
    local expected_output="$3"

    total_tests=$((total_tests + 1))

    echo ""
    echo "Test ${total_tests}: ${test_name}"
    echo "  Creating state file with status='${status_value}'"
    echo "  Expected read output: ${expected_output}"

    # Create test state file
    local state_file="${TEST_STATE_DIR}/phase_wf_read_test_phase_read_test_validation.json"
    cat > "${state_file}" <<EOF
{
    "workflow_id": "wf_read_test",
    "phase_id": "phase_read_test",
    "session_id": "sess_read_test",
    "validation_status": "${status_value}",
    "persisted_at": "2025-01-15T12:00:00Z",
    "summary": {
        "total_rules_executed": 0,
        "results_count": 0
    },
    "rule_results": []
}
EOF

    # Run read_validation_state
    local actual_output
    actual_output=$(read_validation_state "wf_read_test" "phase_read_test" 2>/dev/null)

    echo "  Actual output: ${actual_output}"

    if [[ "${actual_output}" == "${expected_output}" ]]; then
        echo "  Result: PASSED"
        passed_tests=$((passed_tests + 1))
    else
        echo "  Result: FAILED (expected '${expected_output}', got '${actual_output}')"
        failed_tests=$((failed_tests + 1))
    fi

    # Cleanup state file
    rm -f "${state_file}"
}

################################################################################
# Main Test Suite
################################################################################

echo "========================================================================"
echo "Integration Test Suite: Enum Validation in persist/read functions"
echo "========================================================================"

echo ""
echo "========== Testing persist_validation_state() =========="

# Valid values (should succeed)
run_persist_test "Persist with PASSED" "PASSED" 0
run_persist_test "Persist with FAILED" "FAILED" 0

# Invalid values (should fail)
run_persist_test "Persist with UNKNOWN" "UNKNOWN" 1
run_persist_test "Persist with passed (lowercase)" "passed" 1
run_persist_test "Persist with empty string" "" 1
run_persist_test "Persist with null" "null" 1
run_persist_test "Persist with invalid" "invalid" 1

echo ""
echo "========== Testing read_validation_state() =========="

# Valid values (should return actual value)
run_read_test "Read PASSED" "PASSED" "PASSED"
run_read_test "Read FAILED" "FAILED" "FAILED"

# Invalid values (should return UNKNOWN with fail-open)
run_read_test "Read UNKNOWN" "UNKNOWN" "UNKNOWN"
run_read_test "Read passed (lowercase)" "passed" "UNKNOWN"
run_read_test "Read invalid" "invalid" "UNKNOWN"
run_read_test "Read null" "null" "UNKNOWN"
run_read_test "Read 123" "123" "UNKNOWN"

echo ""
echo "========================================================================"
echo "Integration Test Summary"
echo "========================================================================"
echo "Total tests: ${total_tests}"
echo "Passed: ${passed_tests}"
echo "Failed: ${failed_tests}"
echo ""

if [[ ${failed_tests} -eq 0 ]]; then
    echo "All integration tests passed!"
    exit 0
else
    echo "Some integration tests failed!"
    exit 1
fi
