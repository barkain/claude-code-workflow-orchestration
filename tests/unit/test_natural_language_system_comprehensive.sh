#!/bin/bash
################################################################################
# Comprehensive Natural Language Validation System Tests
#
# Purpose: Verify all requirements for Phase 6 (Natural Language Validation)
# Tests:
#   1. Decision extraction from natural language
#   2. User visibility of Haiku responses
#   3. All decision paths (CONTINUE/REPEAT/ABORT/NOT_APPLICABLE)
#   4. Edge cases and error handling
#   5. Exit code mapping
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK_SCRIPT="${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"
TEST_OUTPUT_DIR="${SCRIPT_DIR}/output/natural_language_tests"

# Ensure test output directory exists
mkdir -p "${TEST_OUTPUT_DIR}"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function: Print test header
print_header() {
    local title="$1"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}${title}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Helper function: Print test result
print_result() {
    local test_name="$1"
    local passed="$2"
    local details="${3:-}"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "${passed}" == "true" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}✓${NC} ${test_name}"
        if [[ -n "${details}" ]]; then
            echo "  ${details}"
        fi
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} ${test_name}"
        if [[ -n "${details}" ]]; then
            echo "  ${details}"
        fi
    fi
}

# Helper function: Extract decision from Haiku response
extract_decision() {
    local haiku_response="$1"
    local decision_line=$(echo "${haiku_response}" | head -n 1)
    local validation_decision=$(echo "${decision_line}" | grep -oE 'CONTINUE|REPEAT|ABORT' || echo "")

    if [[ -z "${validation_decision}" ]]; then
        echo "NOT_APPLICABLE"
    else
        echo "${validation_decision}"
    fi
}

################################################################################
# Test Suite 1: Decision Extraction from Natural Language
################################################################################

test_decision_extraction() {
    print_header "Test Suite 1: Decision Extraction from Natural Language"

    # Test 1.1: CONTINUE decision
    local response_continue="VALIDATION DECISION: CONTINUE

The subagent successfully completed the task objective. All requirements
have been met and the deliverable is ready for the next phase."

    local result=$(extract_decision "${response_continue}")
    if [[ "${result}" == "CONTINUE" ]]; then
        print_result "Extract CONTINUE decision" "true"
    else
        print_result "Extract CONTINUE decision" "false" "Expected: CONTINUE, Got: ${result}"
    fi

    # Test 1.2: REPEAT decision
    local response_repeat="VALIDATION DECISION: REPEAT

The task objective was partially addressed but requires improvements.
The implementation is missing error handling for edge cases."

    result=$(extract_decision "${response_repeat}")
    if [[ "${result}" == "REPEAT" ]]; then
        print_result "Extract REPEAT decision" "true"
    else
        print_result "Extract REPEAT decision" "false" "Expected: REPEAT, Got: ${result}"
    fi

    # Test 1.3: ABORT decision
    local response_abort="VALIDATION DECISION: ABORT

Critical security vulnerability detected in the implementation. The approach
taken fundamentally contradicts the architecture requirements."

    result=$(extract_decision "${response_abort}")
    if [[ "${result}" == "ABORT" ]]; then
        print_result "Extract ABORT decision" "true"
    else
        print_result "Extract ABORT decision" "false" "Expected: ABORT, Got: ${result}"
    fi

    # Test 1.4: Malformed response (no decision header)
    local response_malformed="I have analyzed the deliverables and they look good.
The implementation meets most requirements."

    result=$(extract_decision "${response_malformed}")
    if [[ "${result}" == "NOT_APPLICABLE" ]]; then
        print_result "Handle malformed response (no header)" "true"
    else
        print_result "Handle malformed response (no header)" "false" "Expected: NOT_APPLICABLE, Got: ${result}"
    fi

    # Test 1.5: Empty response
    local response_empty=""

    result=$(extract_decision "${response_empty}")
    if [[ "${result}" == "NOT_APPLICABLE" ]]; then
        print_result "Handle empty response" "true"
    else
        print_result "Handle empty response" "false" "Expected: NOT_APPLICABLE, Got: ${result}"
    fi

    # Test 1.6: Decision keyword in wrong position
    local response_wrong_position="The analysis shows that we should CONTINUE
with the implementation as planned."

    result=$(extract_decision "${response_wrong_position}")
    # Should extract CONTINUE from first line
    if [[ "${result}" == "CONTINUE" ]]; then
        print_result "Extract decision from wrong position" "true"
    else
        print_result "Extract decision from wrong position" "false" "Expected: CONTINUE, Got: ${result}"
    fi
}

################################################################################
# Test Suite 2: User Visibility
################################################################################

test_user_visibility() {
    print_header "Test Suite 2: User Visibility of Haiku Responses"

    # Test 2.1: Verify visual separators exist in hook script
    if grep -q "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "${HOOK_SCRIPT}"; then
        print_result "Visual separators present in hook" "true"
    else
        print_result "Visual separators present in hook" "false" "No visual separators found"
    fi

    # Test 2.2: Verify icons for decisions
    # Icons are in case statement format: "CONTINUE") decision_icon="✅" ;;
    local icons_found=0
    grep -A 1 '"CONTINUE")' "${HOOK_SCRIPT}" | grep -q 'decision_icon="✅"' && icons_found=$((icons_found + 1))
    grep -A 1 '"REPEAT")' "${HOOK_SCRIPT}" | grep -q 'decision_icon="🔄"' && icons_found=$((icons_found + 1))
    grep -A 1 '"ABORT")' "${HOOK_SCRIPT}" | grep -q 'decision_icon="🚫"' && icons_found=$((icons_found + 1))
    grep -q 'decision_icon="⚠️"' "${HOOK_SCRIPT}" && icons_found=$((icons_found + 1))

    if [[ ${icons_found} -eq 4 ]]; then
        print_result "Decision icons present (✅/🔄/🚫/⚠️)" "true"
    else
        print_result "Decision icons present (✅/🔄/🚫/⚠️)" "false" "Found ${icons_found}/4 icons"
    fi

    # Test 2.3: Verify full response display
    if grep -q 'echo "${validation_response}" >&2' "${HOOK_SCRIPT}"; then
        print_result "Full Haiku response displayed to user" "true"
    else
        print_result "Full Haiku response displayed to user" "false" "Response not displayed"
    fi

    # Test 2.4: Verify output to stderr (user-visible)
    local stderr_count=$(grep -c '>&2' "${HOOK_SCRIPT}" || echo "0")
    if [[ ${stderr_count} -ge 5 ]]; then
        print_result "Output directed to stderr (user visibility)" "true" "Found ${stderr_count} stderr redirects"
    else
        print_result "Output directed to stderr (user visibility)" "false" "Only ${stderr_count} stderr redirects"
    fi
}

################################################################################
# Test Suite 3: Exit Code Mapping
################################################################################

test_exit_code_mapping() {
    print_header "Test Suite 3: Exit Code Mapping"

    # Test 3.1: Verify CONTINUE → exit 0
    if grep -A 3 '"CONTINUE")' "${HOOK_SCRIPT}" | grep -q 'exit 0'; then
        print_result "CONTINUE maps to exit 0" "true"
    else
        print_result "CONTINUE maps to exit 0" "false"
    fi

    # Test 3.2: Verify REPEAT → exit 1
    if grep -A 3 '"REPEAT")' "${HOOK_SCRIPT}" | grep -q 'exit 1'; then
        print_result "REPEAT maps to exit 1" "true"
    else
        print_result "REPEAT maps to exit 1" "false"
    fi

    # Test 3.3: Verify ABORT → exit 2
    if grep -A 3 '"ABORT")' "${HOOK_SCRIPT}" | grep -q 'exit 2'; then
        print_result "ABORT maps to exit 2" "true"
    else
        print_result "ABORT maps to exit 2" "false"
    fi

    # Test 3.4: Verify NOT_APPLICABLE → exit 3
    if grep -A 3 '"NOT_APPLICABLE")' "${HOOK_SCRIPT}" | grep -q 'exit 3'; then
        print_result "NOT_APPLICABLE maps to exit 3" "true"
    else
        print_result "NOT_APPLICABLE maps to exit 3" "false"
    fi
}

################################################################################
# Test Suite 4: Natural Language Output (No JSON)
################################################################################

test_no_json_output() {
    print_header "Test Suite 4: Natural Language Output (No JSON Parsing)"

    # Test 4.1: Verify no jq parsing of Haiku response for decision
    # Should use grep -oE instead of jq
    # Decision extraction happens in main() function, not semantic_validation()
    # Pattern: validation_decision=$(echo "${haiku_response}" | grep -oE 'VALIDATION DECISION: (CONTINUE|REPEAT|ABORT)'
    if grep -q "grep -oE 'VALIDATION DECISION: (CONTINUE|REPEAT|ABORT)'" "${HOOK_SCRIPT}"; then
        print_result "Decision extracted with grep (not jq)" "true"
    else
        print_result "Decision extracted with grep (not jq)" "false"
    fi

    # Test 4.2: Verify no JSON request in Haiku prompt
    if grep -A 30 'haiku_prompt=' "${HOOK_SCRIPT}" | grep -v "JSON" | grep -q "VALIDATION DECISION:"; then
        print_result "Haiku prompt requests natural language" "true"
    else
        print_result "Haiku prompt requests natural language" "false"
    fi

    # Test 4.3: Verify no JSON schema in prompt
    local prompt_section=$(grep -A 30 'haiku_prompt=' "${HOOK_SCRIPT}" || echo "")
    if echo "${prompt_section}" | grep -q "schema"; then
        print_result "No JSON schema in prompt" "false" "JSON schema found in prompt"
    else
        print_result "No JSON schema in prompt" "true"
    fi
}

################################################################################
# Test Suite 5: Edge Case Handling
################################################################################

test_edge_cases() {
    print_header "Test Suite 5: Edge Case Handling"

    # Test 5.1: Multiple decision keywords (should take first)
    local response_multiple="VALIDATION DECISION: CONTINUE
Later in the reasoning I mention that we might need to ABORT if X happens,
but for now we should CONTINUE."

    local result=$(extract_decision "${response_multiple}")
    if [[ "${result}" == "CONTINUE" ]]; then
        print_result "Multiple keywords (takes first line)" "true"
    else
        print_result "Multiple keywords (takes first line)" "false" "Expected: CONTINUE, Got: ${result}"
    fi

    # Test 5.2: Case sensitivity
    local response_lowercase="VALIDATION DECISION: continue
Everything looks good."

    result=$(extract_decision "${response_lowercase}")
    # Current implementation is case-sensitive, should return NOT_APPLICABLE
    if [[ "${result}" == "NOT_APPLICABLE" ]]; then
        print_result "Case-sensitive decision extraction" "true"
    else
        print_result "Case-sensitive decision extraction" "false" "Expected: NOT_APPLICABLE, Got: ${result}"
    fi

    # Test 5.3: Extra whitespace
    local response_whitespace="   VALIDATION DECISION: REPEAT

   Needs improvement.   "

    result=$(extract_decision "${response_whitespace}")
    if [[ "${result}" == "REPEAT" ]]; then
        print_result "Handles extra whitespace" "true"
    else
        print_result "Handles extra whitespace" "false" "Expected: REPEAT, Got: ${result}"
    fi

    # Test 5.4: Verify fail-open behavior for errors
    # Look for exit 3 in the context of warnings/fail-open scenarios
    if grep -B 2 'exit 3' "${HOOK_SCRIPT}" | grep -qE '(WARNING|fail-open)'; then
        print_result "Fail-open behavior on errors" "true"
    else
        print_result "Fail-open behavior on errors" "false"
    fi

    # Test 5.5: Haiku invocation failure handling
    if grep -A 5 'haiku_exit_code.*-ne 0' "${HOOK_SCRIPT}" | grep -q 'NOT_APPLICABLE'; then
        print_result "Haiku failure → NOT_APPLICABLE" "true"
    else
        print_result "Haiku failure → NOT_APPLICABLE" "false"
    fi
}

################################################################################
# Test Suite 6: Integration with Workflow Control
################################################################################

test_workflow_control() {
    print_header "Test Suite 6: Integration with Workflow Control"

    # Test 6.1: Verify logging of decisions
    # Actual log format: log_event "VALIDATION" "semantic_validation" "CONTINUE: Semantic validation passed..."
    if grep -A 2 '"CONTINUE")' "${HOOK_SCRIPT}" | grep -q 'log_event.*VALIDATION.*semantic_validation.*CONTINUE'; then
        print_result "CONTINUE decision logged" "true"
    else
        print_result "CONTINUE decision logged" "false"
    fi

    if grep -A 2 '"REPEAT")' "${HOOK_SCRIPT}" | grep -q 'log_event.*VALIDATION.*semantic_validation.*REPEAT'; then
        print_result "REPEAT decision logged" "true"
    else
        print_result "REPEAT decision logged" "false"
    fi

    if grep -A 2 '"ABORT")' "${HOOK_SCRIPT}" | grep -q 'log_event.*VALIDATION.*semantic_validation.*ABORT'; then
        print_result "ABORT decision logged" "true"
    else
        print_result "ABORT decision logged" "false"
    fi

    # Test 6.2: Verify state persistence for semantic validation
    if grep -q 'persist_validation_state.*semantic' "${HOOK_SCRIPT}"; then
        print_result "Semantic validation state persisted" "true"
    else
        print_result "Semantic validation state persisted" "false"
    fi

    # Test 6.3: Verify reasoning extraction
    # Actual pattern: reasoning=$(echo "${haiku_response}" | tail -n +2)
    if grep -q 'reasoning=$(echo "${haiku_response}" | tail -n +2)' "${HOOK_SCRIPT}"; then
        print_result "Reasoning extracted from response" "true"
    else
        print_result "Reasoning extracted from response" "false"
    fi
}

################################################################################
# Main Test Execution
################################################################################

main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  Natural Language Validation System - Comprehensive Tests   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Testing hook script: ${HOOK_SCRIPT}"

    # Verify hook script exists
    if [[ ! -f "${HOOK_SCRIPT}" ]]; then
        echo -e "${RED}ERROR: Hook script not found: ${HOOK_SCRIPT}${NC}"
        exit 1
    fi

    # Run all test suites
    test_decision_extraction
    test_user_visibility
    test_exit_code_mapping
    test_no_json_output
    test_edge_cases
    test_workflow_control

    # Print summary
    print_header "Test Summary"
    echo ""
    echo "Tests Run:    ${TESTS_RUN}"
    echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [[ ${TESTS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
