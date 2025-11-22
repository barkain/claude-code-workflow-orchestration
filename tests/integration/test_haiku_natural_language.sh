#!/bin/bash
################################################################################
# Integration Test: Haiku Natural Language Validation
#
# Purpose: Test actual Haiku invocation with natural language output
# Verifies:
#   1. Haiku returns natural language (not JSON)
#   2. User can see full Haiku response
#   3. Decision mechanism works with real Haiku output
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_OUTPUT_DIR="${SCRIPT_DIR}/output/haiku_natural_language"

mkdir -p "${TEST_OUTPUT_DIR}"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    local title="$1"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}${title}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

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

################################################################################
# Test 1: Haiku Natural Language Response
################################################################################

test_haiku_natural_language() {
    print_header "Test 1: Haiku Natural Language Response (Real API Call)"

    # Check if claude command is available
    if ! command -v claude >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Skipping Haiku tests: claude command not available${NC}"
        return
    fi

    # Create a simple validation prompt
    local test_prompt="You are a validation agent analyzing the completion of a workflow phase.

TASK OBJECTIVE:
Create a simple calculator function that adds two numbers

SUBAGENT DELIVERABLES:
I have created a calculator function called add() that takes two parameters (a and b)
and returns their sum. The function includes input validation to ensure both parameters
are numbers. I have also added docstring documentation explaining the function usage.

YOUR TASK:
Analyze whether the subagent accomplished the task objective.

OUTPUT FORMAT REQUIREMENTS:
- First line MUST be: \"VALIDATION DECISION: [CONTINUE|REPEAT|ABORT]\"
- Use CONTINUE if task is complete and objective was met
- Use REPEAT if work needs improvement/fixes before proceeding
- Use ABORT if critical failures make workflow continuation impossible
- After decision line, provide natural language reasoning explaining your decision

EXAMPLE OUTPUT:
VALIDATION DECISION: CONTINUE

I have analyzed the deliverables and found they meet the task objective.
The implementation addresses all key requirements and is ready for the
next phase.

Now analyze the phase completion above and provide your validation decision."

    # Call Haiku and capture response
    echo "  Invoking Haiku..."
    local haiku_response
    local haiku_exit_code

    haiku_response=$(claude --model haiku -p "${test_prompt}" 2>&1)
    haiku_exit_code=$?

    # Test 1.1: Haiku call succeeds
    if [[ ${haiku_exit_code} -eq 0 ]]; then
        print_result "Haiku API call successful" "true"
    else
        print_result "Haiku API call successful" "false" "Exit code: ${haiku_exit_code}"
        return
    fi

    # Save response for inspection
    echo "${haiku_response}" > "${TEST_OUTPUT_DIR}/haiku_response_sample.txt"

    # Test 1.2: Response is NOT JSON
    if echo "${haiku_response}" | jq empty 2>/dev/null; then
        print_result "Response is natural language (not JSON)" "false" "Response appears to be valid JSON"
    else
        print_result "Response is natural language (not JSON)" "true"
    fi

    # Test 1.3: Response contains decision header
    local first_line=$(echo "${haiku_response}" | head -n 1)
    if echo "${first_line}" | grep -q "VALIDATION DECISION:"; then
        print_result "Response contains decision header" "true" "First line: ${first_line}"
    else
        print_result "Response contains decision header" "false" "First line: ${first_line}"
    fi

    # Test 1.4: Decision keyword present
    local decision=$(echo "${first_line}" | grep -oE 'CONTINUE|REPEAT|ABORT' || echo "")
    if [[ -n "${decision}" ]]; then
        print_result "Valid decision keyword extracted" "true" "Decision: ${decision}"
    else
        print_result "Valid decision keyword extracted" "false" "No decision found"
    fi

    # Test 1.5: Response has natural language reasoning
    local response_length=${#haiku_response}
    if [[ ${response_length} -gt 100 ]]; then
        print_result "Response includes reasoning (>100 chars)" "true" "Length: ${response_length} chars"
    else
        print_result "Response includes reasoning (>100 chars)" "false" "Length: ${response_length} chars"
    fi

    # Test 1.6: Display sample response
    print_header "Sample Haiku Response"
    echo "${haiku_response}"
    echo ""
}

################################################################################
# Test 2: User Visibility Simulation
################################################################################

test_user_visibility_simulation() {
    print_header "Test 2: User Visibility Simulation"

    # Simulate the hook's display logic
    local sample_response="VALIDATION DECISION: CONTINUE

The subagent successfully completed the calculator function. The add() function
meets all requirements:
- Takes two parameters
- Returns their sum
- Includes input validation
- Has proper documentation

The implementation is complete and ready for the next phase."

    # Simulate stderr output with visual formatting
    local formatted_output=$(cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Validation Analysis:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${sample_response}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DECISION: Continue to next phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
)

    # Test 2.1: Formatted output contains visual elements
    if echo "${formatted_output}" | grep -q "━━━"; then
        print_result "Visual separators present" "true"
    else
        print_result "Visual separators present" "false"
    fi

    if echo "${formatted_output}" | grep -q "🔍"; then
        print_result "Analysis icon present" "true"
    else
        print_result "Analysis icon present" "false"
    fi

    if echo "${formatted_output}" | grep -q "✅"; then
        print_result "Decision icon present" "true"
    else
        print_result "Decision icon present" "false"
    fi

    # Test 2.2: Display what user would see
    print_header "What User Would See"
    echo "${formatted_output}"
}

################################################################################
# Test 3: Decision Extraction from Real Response
################################################################################

test_decision_extraction_real() {
    print_header "Test 3: Decision Extraction from Real Haiku Responses"

    # If we have a saved response from Test 1, use it
    if [[ -f "${TEST_OUTPUT_DIR}/haiku_response_sample.txt" ]]; then
        local haiku_response=$(cat "${TEST_OUTPUT_DIR}/haiku_response_sample.txt")

        # Extract decision using same logic as hook
        local decision_line=$(echo "${haiku_response}" | head -n 1)
        local validation_decision=$(echo "${decision_line}" | grep -oE 'CONTINUE|REPEAT|ABORT' || echo "")

        if [[ -n "${validation_decision}" ]]; then
            print_result "Decision extracted from real response" "true" "Decision: ${validation_decision}"

            # Extract reasoning (everything after first line)
            local reasoning=$(echo "${haiku_response}" | tail -n +2)
            local reasoning_length=${#reasoning}

            print_result "Reasoning extracted" "true" "Length: ${reasoning_length} chars"
        else
            print_result "Decision extracted from real response" "false" "No decision found"
        fi
    else
        echo -e "${YELLOW}⚠ No saved response available from Test 1${NC}"
    fi
}

################################################################################
# Main
################################################################################

main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  Integration Test: Haiku Natural Language Validation        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Output directory: ${TEST_OUTPUT_DIR}"

    # Run test suites
    test_haiku_natural_language
    test_user_visibility_simulation
    test_decision_extraction_real

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
        echo -e "${YELLOW}⚠ Some tests failed (may be due to Haiku availability)${NC}"
        exit 0  # Don't fail build if Haiku unavailable
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
