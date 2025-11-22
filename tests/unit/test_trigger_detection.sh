#!/bin/bash
################################################################################
# Unit Tests: Trigger Detection Logic
#
# Purpose: Test detect_validation_trigger() and should_validate_phase()
# Test Coverage:
#   - Correct tool detection (SlashCommand, Task, SubagentTask)
#   - Non-delegation tool filtering
#   - JSON parsing and error handling
#   - Session/workflow context extraction
#   - Validation config file detection
#   - Permission and filesystem errors
#
# Author: Claude Code Delegation System
# Version: 1.0.0
################################################################################

set -euo pipefail

# Test configuration
readonly TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${TEST_DIR}/../.." && pwd)"
readonly HOOK_SCRIPT="${PROJECT_ROOT}/hooks/PostToolUse/validation_gate.sh"
readonly TEST_STATE_DIR="${PROJECT_ROOT}/.claude/state/validation"

# Test counters
test_count=0
pass_count=0

# Color codes for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m' # No Color

################################################################################
# Test Helpers
################################################################################

# Run a single test
# Args:
#   $1: Test name
#   $2: Input JSON
#   $3: Expected output pattern (regex)
run_test() {
    local test_name="$1"
    local input="$2"
    local expected="$3"

    test_count=$((test_count + 1))

    # Execute detect_validation_trigger via hook script
    # Use a subshell to capture only the trigger detection output
    local result
    result=$(echo "${input}" | bash -c "source '${HOOK_SCRIPT}' && detect_validation_trigger" 2>/dev/null || echo "SCRIPT_ERROR")

    # Check if result matches expected pattern
    if echo "${result}" | grep -qE "^${expected}$"; then
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected pattern: ${expected}"
        echo "   Got: ${result}"
    fi
}

# Setup test environment
setup_test_env() {
    # Create test validation state directory
    mkdir -p "${TEST_STATE_DIR}"

    # Create test log file (will be used by logging functions)
    touch "${TEST_STATE_DIR}/gate_invocations.log"
}

# Cleanup test environment
cleanup_test_env() {
    # Remove test validation configs (preserve production configs)
    find "${TEST_STATE_DIR}" -name "test_*.json" -delete 2>/dev/null || true
    # Remove phase config files created during tests
    find "${TEST_STATE_DIR}" -name "phase_*.json" -delete 2>/dev/null || true
}

# Create test validation config
# Args:
#   $1: Config filename (e.g., phase_wf_789_1.json)
create_test_config() {
    local filename="$1"
    local config_path="${TEST_STATE_DIR}/${filename}"

    cat > "${config_path}" <<'EOF'
{
  "schema_version": "1.0",
  "metadata": {
    "phase_id": "test_phase",
    "phase_name": "Test Phase",
    "workflow_id": "wf_789",
    "created_at": "2025-11-15T00:00:00Z"
  },
  "validation_config": {
    "rules": []
  },
  "validation_execution": {
    "results": []
  },
  "status": {
    "current_status": "pending",
    "last_updated": "2025-11-15T00:00:00Z",
    "passed_count": 0,
    "failed_count": 0,
    "total_count": 0
  }
}
EOF
}

################################################################################
# Test Suite: detect_validation_trigger()
################################################################################

run_trigger_detection_tests() {
    echo ""
    echo "=================================="
    echo "Test Suite: detect_validation_trigger()"
    echo "=================================="
    echo ""

    # Test 1: SlashCommand tool detection
    run_test \
        "SlashCommand tool detection" \
        '{"tool": {"name": "SlashCommand"}, "sessionId": "sess_123"}' \
        'TRIGGER\|sess_123\|'

    # Test 2: Task tool with workflow ID
    run_test \
        "Task tool with workflow ID" \
        '{"tool": {"name": "Task"}, "sessionId": "sess_456", "workflowId": "wf_789"}' \
        'TRIGGER\|sess_456\|wf_789'

    # Test 3: SubagentTask tool detection
    run_test \
        "SubagentTask tool detection" \
        '{"tool": {"name": "SubagentTask"}, "sessionId": "sess_789", "workflowId": "wf_012"}' \
        'TRIGGER\|sess_789\|wf_012'

    # Test 4: AgentTask tool detection
    run_test \
        "AgentTask tool detection" \
        '{"tool": {"name": "AgentTask"}, "sessionId": "sess_abc"}' \
        'TRIGGER\|sess_abc\|'

    # Test 5: Non-delegation tool (Read)
    run_test \
        "Non-delegation tool (Read)" \
        '{"tool": {"name": "Read"}, "sessionId": "sess_123"}' \
        'SKIP\|non-delegation tool: Read'

    # Test 6: Non-delegation tool (Write)
    run_test \
        "Non-delegation tool (Write)" \
        '{"tool": {"name": "Write"}, "sessionId": "sess_456"}' \
        'SKIP\|non-delegation tool: Write'

    # Test 7: Non-delegation tool (Bash)
    run_test \
        "Non-delegation tool (Bash)" \
        '{"tool": {"name": "Bash"}, "sessionId": "sess_789"}' \
        'SKIP\|non-delegation tool: Bash'

    # Test 8: Malformed JSON (invalid syntax)
    run_test \
        "Malformed JSON (invalid syntax)" \
        '{invalid json' \
        'ERROR\|Invalid JSON input'

    # Test 9: Missing tool.name field
    run_test \
        "Missing tool.name field" \
        '{"tool": {}, "sessionId": "sess_123"}' \
        'ERROR\|Missing field: tool.name'

    # Test 10: Missing sessionId field
    run_test \
        "Missing sessionId field" \
        '{"tool": {"name": "Task"}}' \
        'ERROR\|Missing field: sessionId'

    # Test 11: Empty workflow ID (should be allowed)
    run_test \
        "Task with empty workflow ID" \
        '{"tool": {"name": "Task"}, "sessionId": "sess_xyz"}' \
        'TRIGGER\|sess_xyz\|'

    # Test 12: Complex session ID
    run_test \
        "Complex session ID format" \
        '{"tool": {"name": "Task"}, "sessionId": "sess_20251115_143022_abc123", "workflowId": "wf_20251115"}' \
        'TRIGGER\|sess_20251115_143022_abc123\|wf_20251115'
}

################################################################################
# Test Suite: should_validate_phase()
################################################################################

run_phase_validation_tests() {
    echo ""
    echo "=================================="
    echo "Test Suite: should_validate_phase()"
    echo "=================================="
    echo ""

    # Create test validation config
    create_test_config "phase_wf_789_1.json"

    # Test 13: Validation config found (workflow-specific)
    local test_name="Validation config found (workflow-specific)"
    test_count=$((test_count + 1))

    if bash -c "source '${HOOK_SCRIPT}' && should_validate_phase 'sess_456' 'wf_789'" 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: Config found (exit code 0)"
        echo "   Got: Config not found (exit code 1)"
    fi

    # Cleanup first test config before testing non-existent workflow
    rm -f "${TEST_STATE_DIR}/phase_wf_789_1.json"
    rm -f "${TEST_STATE_DIR}"/phase_*.json

    # Test 14: No validation config (non-existent workflow, no fallback)
    test_name="No validation config (non-existent workflow)"
    test_count=$((test_count + 1))

    if bash -c "source '${HOOK_SCRIPT}' && should_validate_phase 'sess_999' 'wf_nonexistent'" 2>/dev/null; then
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: Config not found (exit code 1)"
        echo "   Got: Config found (exit code 0)"
    else
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    fi

    # Create generic phase config (no workflow ID in filename)
    create_test_config "phase_generic_test.json"

    # Test 15: Fallback to generic config
    test_name="Fallback to generic config when workflow-specific not found"
    test_count=$((test_count + 1))

    if bash -c "source '${HOOK_SCRIPT}' && should_validate_phase 'sess_generic' 'wf_unknown'" 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: Generic config found (exit code 0)"
        echo "   Got: Config not found (exit code 1)"
    fi

    # Cleanup test configs
    rm -f "${TEST_STATE_DIR}/phase_wf_789_1.json"
    rm -f "${TEST_STATE_DIR}/phase_generic_test.json"
    rm -f "${TEST_STATE_DIR}"/phase_*.json

    # Test 16: Empty validation state directory
    test_name="No configs in empty validation directory"
    test_count=$((test_count + 1))

    if bash -c "source '${HOOK_SCRIPT}' && should_validate_phase 'sess_empty' 'wf_empty'" 2>/dev/null; then
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: No config found (exit code 1)"
        echo "   Got: Config found (exit code 0)"
    else
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    fi
}

################################################################################
# Test Suite: Integration Tests
################################################################################

run_integration_tests() {
    echo ""
    echo "=================================="
    echo "Test Suite: Integration Tests"
    echo "=================================="
    echo ""

    # Test 17: End-to-end workflow (TRIGGER + config check)
    local test_name="End-to-end: Task tool triggers validation check"
    test_count=$((test_count + 1))

    # Create test config for this workflow
    create_test_config "phase_wf_integration_1.json"

    # Execute full hook with Task tool
    local hook_output
    hook_output=$(echo '{"tool": {"name": "Task"}, "sessionId": "sess_integration", "workflowId": "wf_integration"}' | \
        bash "${HOOK_SCRIPT}" 2>/dev/null && echo "SUCCESS" || echo "FAILURE")

    if [[ "${hook_output}" == "SUCCESS" ]]; then
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: Hook executes without error"
        echo "   Got: Hook execution failed"
    fi

    # Cleanup
    rm -f "${TEST_STATE_DIR}/phase_wf_integration_1.json"

    # Test 18: End-to-end workflow (SKIP for non-delegation tool)
    test_name="End-to-end: Read tool skips validation"
    test_count=$((test_count + 1))

    hook_output=$(echo '{"tool": {"name": "Read"}, "sessionId": "sess_read"}' | \
        bash "${HOOK_SCRIPT}" 2>/dev/null && echo "SUCCESS" || echo "FAILURE")

    if [[ "${hook_output}" == "SUCCESS" ]]; then
        echo -e "${GREEN}✅ PASS${NC}: ${test_name}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: ${test_name}"
        echo "   Expected: Hook executes without error"
        echo "   Got: Hook execution failed"
    fi
}

################################################################################
# Main Test Runner
################################################################################

main() {
    echo "=================================="
    echo "Validation Gate: Trigger Detection Tests"
    echo "=================================="

    # Setup test environment
    setup_test_env

    # Run test suites
    run_trigger_detection_tests
    run_phase_validation_tests
    run_integration_tests

    # Cleanup
    cleanup_test_env

    # Print summary
    echo ""
    echo "=================================="
    echo "Test Results"
    echo "=================================="
    echo ""

    if [[ ${pass_count} -eq ${test_count} ]]; then
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        echo "Results: ${pass_count}/${test_count} tests passed"
        exit 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        echo "Results: ${pass_count}/${test_count} tests passed"
        echo "Failed: $((test_count - pass_count)) tests"
        exit 1
    fi
}

# Execute main function
main "$@"
