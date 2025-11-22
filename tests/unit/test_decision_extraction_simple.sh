#!/bin/bash
################################################################################
# Simple Decision Extraction Tests
#
# Purpose: Test decision extraction logic without full validation gate execution
################################################################################

set -euo pipefail

# Test decision extraction function (extracted from validation_gate.sh)
extract_decision() {
    local haiku_response="$1"

    # Extract first line
    local decision_line=$(echo "${haiku_response}" | head -n 1)

    # Extract keyword using grep -oE
    local validation_decision=$(echo "${decision_line}" | grep -oE 'CONTINUE|REPEAT|ABORT' || echo "")

    if [[ -z "${validation_decision}" ]]; then
        echo "NOT_APPLICABLE"
    else
        echo "${validation_decision}"
    fi
}

# Test cases
echo "Testing Decision Extraction:"
echo ""

# Test 1: CONTINUE
response1="VALIDATION DECISION: CONTINUE

Phase is complete and meets requirements."
result1=$(extract_decision "${response1}")
echo "Test 1 - CONTINUE: ${result1} $([ "${result1}" = "CONTINUE" ] && echo "✓" || echo "✗")"

# Test 2: REPEAT
response2="VALIDATION DECISION: REPEAT

Phase needs improvements before proceeding."
result2=$(extract_decision "${response2}")
echo "Test 2 - REPEAT: ${result2} $([ "${result2}" = "REPEAT" ] && echo "✓" || echo "✗")"

# Test 3: ABORT
response3="VALIDATION DECISION: ABORT

Critical failure detected, cannot continue."
result3=$(extract_decision "${response3}")
echo "Test 3 - ABORT: ${result3} $([ "${result3}" = "ABORT" ] && echo "✓" || echo "✗")"

# Test 4: Malformed (no header)
response4="I analyzed the phase and it looks good."
result4=$(extract_decision "${response4}")
echo "Test 4 - Malformed: ${result4} $([ "${result4}" = "NOT_APPLICABLE" ] && echo "✓" || echo "✗")"

# Test 5: Wrong format
response5="Decision: CONTINUE (not in correct format)"
result5=$(extract_decision "${response5}")
echo "Test 5 - Wrong format: ${result5} $([ "${result5}" = "CONTINUE" ] && echo "✓" || echo "✗")"

echo ""
echo "All decision extraction tests completed!"
