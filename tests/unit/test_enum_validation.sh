#!/bin/bash
################################################################################
# Test Script: Enum Validation for validation_status field
#
# Purpose: Test validate_validation_status() function with valid and invalid values
# Location: tests/unit/test_enum_validation.sh
#
# Author: Claude Code Delegation System
# Version: 1.0.0
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_GATE_SCRIPT="${SCRIPT_DIR}/../../hooks/PostToolUse/validation_gate.sh"

# Source the validation_gate.sh script to get access to functions
# Note: This will set SCRIPT_DIR, PROJECT_ROOT, etc. as readonly
source "${VALIDATION_GATE_SCRIPT}"

# Override log_event to test logging without creating actual log files
log_event() {
    echo "[LOG] Event: $1, Tool: $2, Details: $3"
}

################################################################################
# Test Functions
################################################################################

# Test counter
total_tests=0
passed_tests=0
failed_tests=0

# Run a single test
run_test() {
    local test_name="$1"
    local test_value="$2"
    local expected_exit_code="$3"

    total_tests=$((total_tests + 1))

    echo ""
    echo "Test ${total_tests}: ${test_name}"
    echo "  Input: '${test_value}'"
    echo "  Expected exit code: ${expected_exit_code}"

    # Run validation
    local actual_exit_code=0
    validate_validation_status "${test_value}" || actual_exit_code=$?

    echo "  Actual exit code: ${actual_exit_code}"

    if [[ ${actual_exit_code} -eq ${expected_exit_code} ]]; then
        echo "  Result: PASSED"
        passed_tests=$((passed_tests + 1))
    else
        echo "  Result: FAILED (expected ${expected_exit_code}, got ${actual_exit_code})"
        failed_tests=$((failed_tests + 1))
    fi
}

################################################################################
# Main Test Suite
################################################################################

echo "========================================================================"
echo "Enum Validation Test Suite"
echo "Testing validate_validation_status() function"
echo "========================================================================"

# Valid values (should return 0)
run_test "Valid value: PASSED" "PASSED" 0
run_test "Valid value: FAILED" "FAILED" 0

# Invalid values (should return 1)
run_test "Invalid value: UNKNOWN" "UNKNOWN" 1
run_test "Invalid value: passed (lowercase)" "passed" 1
run_test "Invalid value: failed (lowercase)" "failed" 1
run_test "Invalid value: Passed (mixed case)" "Passed" 1
run_test "Invalid value: Failed (mixed case)" "Failed" 1
run_test "Invalid value: PASS (truncated)" "PASS" 1
run_test "Invalid value: FAIL (truncated)" "FAIL" 1
run_test "Invalid value: empty string" "" 1
run_test "Invalid value: null" "null" 1
run_test "Invalid value: invalid" "invalid" 1
run_test "Invalid value: 123 (numeric)" "123" 1
run_test "Invalid value: true (boolean)" "true" 1
run_test "Invalid value: false (boolean)" "false" 1

# Test with whitespace
run_test "Invalid value: PASSED with leading space" " PASSED" 1
run_test "Invalid value: PASSED with trailing space" "PASSED " 1

echo ""
echo "========================================================================"
echo "Test Summary"
echo "========================================================================"
echo "Total tests: ${total_tests}"
echo "Passed: ${passed_tests}"
echo "Failed: ${failed_tests}"
echo ""

if [[ ${failed_tests} -eq 0 ]]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed!"
    exit 1
fi
