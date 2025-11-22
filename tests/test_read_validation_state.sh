#!/bin/bash
################################################################################
# Test Script: read_validation_state() function
#
# Purpose: Test reading validation state from persisted JSON files
# Tests:
#   1. Read PASSED status from valid state file
#   2. Read FAILED status from valid state file
#   3. Handle missing validation_status field gracefully
#   4. Handle missing state file gracefully
#   5. Handle invalid JSON gracefully
################################################################################

set -euo pipefail

# Source the validation_gate.sh script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper function
run_test() {
    local test_name="$1"
    local expected_status="$2"
    local workflow_id="$3"
    local phase_id="$4"

    TESTS_RUN=$((TESTS_RUN + 1))

    echo ""
    echo "Test #${TESTS_RUN}: ${test_name}"
    echo "  Workflow ID: ${workflow_id}"
    echo "  Phase ID: ${phase_id}"
    echo "  Expected Status: ${expected_status}"

    # Call read_validation_state function
    local actual_status
    actual_status=$(read_validation_state "${workflow_id}" "${phase_id}")

    echo "  Actual Status: ${actual_status}"

    # Check result
    if [[ "${actual_status}" == "${expected_status}" ]]; then
        echo "  Result: PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "  Result: FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo "================================"
echo "Testing read_validation_state()"
echo "================================"

# Test 1: Read PASSED status from valid state file
run_test "Read PASSED status" "PASSED" "test_workflow" "phase1"

# Test 2: Read FAILED status from valid state file
run_test "Read FAILED status" "FAILED" "test_workflow" "phase2"

# Test 3: Handle missing validation_status field
run_test "Missing validation_status field" "UNKNOWN" "test_workflow" "invalid"

# Test 4: Handle missing state file
run_test "Missing state file" "UNKNOWN" "test_workflow" "nonexistent"

# Test 5: Create invalid JSON file and test handling
echo "Creating invalid JSON file for test..."
INVALID_JSON_FILE="${PROJECT_ROOT}/.claude/state/validation/phase_test_workflow_badjson_validation.json"
echo "{ invalid json" > "${INVALID_JSON_FILE}"
run_test "Invalid JSON file" "UNKNOWN" "test_workflow" "badjson"
rm -f "${INVALID_JSON_FILE}"

# Test 6: Create file with invalid status value
echo "Creating file with invalid status value..."
INVALID_STATUS_FILE="${PROJECT_ROOT}/.claude/state/validation/phase_test_workflow_badstatus_validation.json"
cat > "${INVALID_STATUS_FILE}" <<EOF
{
  "workflow_id": "test_workflow",
  "phase_id": "badstatus",
  "validation_status": "INVALID_STATUS"
}
EOF
run_test "Invalid status value" "UNKNOWN" "test_workflow" "badstatus"
rm -f "${INVALID_STATUS_FILE}"

# Print summary
echo ""
echo "================================"
echo "Test Summary"
echo "================================"
echo "Tests Run: ${TESTS_RUN}"
echo "Tests Passed: ${TESTS_PASSED}"
echo "Tests Failed: ${TESTS_FAILED}"
echo ""

if [[ ${TESTS_FAILED} -eq 0 ]]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed!"
    exit 1
fi
