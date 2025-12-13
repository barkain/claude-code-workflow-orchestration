#!/bin/bash
# run_integration_tests.sh - Master test runner for integration tests

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$SCRIPT_DIR"

# Test execution mode
FAIL_FAST=0
VERBOSE=0
COVERAGE_MODE=0

# Parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --fail-fast)
                FAIL_FAST=1
                shift
                ;;
            --verbose|-v)
                VERBOSE=1
                shift
                ;;
            --coverage)
                COVERAGE_MODE=1
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Run all test suites for Claude Code Delegation System

Automatically discovers and executes all test_*.sh files in the tests directory
and subdirectories (unit/, integration/, verification/, etc.)

OPTIONS:
    --fail-fast     Stop at first test failure
    --verbose, -v   Show detailed test output
    --coverage      Run coverage analysis
    --help, -h      Show this help message

EXAMPLES:
    # Run all tests
    $0

    # Run with fail-fast mode
    $0 --fail-fast

    # Run with verbose output
    $0 --verbose

    # Run with coverage analysis
    $0 --coverage
EOF
}

# Check prerequisites
check_prerequisites() {
    echo -e "${CYAN}Checking prerequisites...${NC}"

    # Check for required commands
    local missing_deps=()

    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    if ! command -v bash &> /dev/null; then
        missing_deps+=("bash")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}Missing dependencies: ${missing_deps[*]}${NC}"
        exit 1
    fi

    # Check for test files
    if [[ ! -d "$TESTS_DIR" ]]; then
        echo -e "${RED}Tests directory not found: $TESTS_DIR${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Prerequisites satisfied"
    echo ""
}

# Run single test suite
run_test_suite() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)

    echo -e "${CYAN}=========================================${NC}"
    echo -e "${CYAN}Running: $test_name${NC}"
    echo -e "${CYAN}=========================================${NC}"

    local start_time=$(date +%s)
    local exit_code=0

    if [[ $VERBOSE -eq 1 ]]; then
        bash "$test_file" || exit_code=$?
    else
        bash "$test_file" 2>&1 | tee "/tmp/${test_name}_output.log" || exit_code=$?
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✓${NC} $test_name PASSED (${duration}s)"
        return 0
    else
        echo -e "${RED}✗${NC} $test_name FAILED (${duration}s)"

        if [[ $VERBOSE -eq 0 ]]; then
            echo -e "${YELLOW}See /tmp/${test_name}_output.log for details${NC}"
        fi

        return 1
    fi
}

# Run all integration tests
run_all_tests() {
    local test_files=()

    # Dynamically discover all test_*.sh files in tests directory and subdirectories
    # Exclude test_utils.sh as it contains helper functions, not tests
    while IFS= read -r -d '' test_file; do
        local basename=$(basename "$test_file")
        # Skip utility files that aren't actual test suites
        if [[ "$basename" != "test_utils.sh" ]]; then
            test_files+=("$test_file")
        fi
    done < <(find "$TESTS_DIR" -name 'test_*.sh' -type f -print0 | sort -z)

    # If no tests to run, report success
    if [[ ${#test_files[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No test files found in $TESTS_DIR${NC}"
        echo ""
        return 0
    fi

    echo -e "${CYAN}Discovered ${#test_files[@]} test suite(s)${NC}"
    echo ""

    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    local failed_test_names=()

    local overall_start=$(date +%s)

    for test_file in "${test_files[@]}"; do
        if [[ ! -f "$test_file" ]]; then
            echo -e "${YELLOW}Warning: Test file not found: $test_file${NC}"
            continue
        fi

        total_tests=$((total_tests + 1))

        if run_test_suite "$test_file"; then
            passed_tests=$((passed_tests + 1))
        else
            failed_tests=$((failed_tests + 1))
            failed_test_names+=("$(basename "$test_file" .sh)")

            if [[ $FAIL_FAST -eq 1 ]]; then
                echo -e "${RED}Stopping due to --fail-fast${NC}"
                break
            fi
        fi

        echo ""
    done

    local overall_end=$(date +%s)
    local overall_duration=$((overall_end - overall_start))

    # Print final summary
    # Use "${failed_test_names[@]:-}" to safely handle empty array in strict mode
    print_final_summary "$total_tests" "$passed_tests" "$failed_tests" "$overall_duration" "${failed_test_names[@]:-}"

    # Return exit code
    [[ $failed_tests -eq 0 ]]
}

# Print final test summary
print_final_summary() {
    local total=$1
    local passed=$2
    local failed=$3
    local duration=$4
    shift 4
    local failed_names=("$@")

    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}TEST SUMMARY${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo -e "Total Test Suites: ${BLUE}$total${NC}"
    echo -e "Passed:            ${GREEN}$passed${NC}"
    echo -e "Failed:            ${RED}$failed${NC}"
    echo -e "Duration:          ${CYAN}${duration}s${NC}"
    echo -e "${BLUE}=========================================${NC}"

    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ SOME TESTS FAILED${NC}"
        echo ""
        echo -e "${RED}Failed test suites:${NC}"
        for name in "${failed_names[@]}"; do
            echo -e "  ${RED}- $name${NC}"
        done
        echo ""
        return 1
    fi
}

# Run coverage analysis
run_coverage_analysis() {
    echo -e "${CYAN}Running coverage analysis...${NC}"
    echo ""

    echo -e "${CYAN}Test Coverage Metrics:${NC}"
    echo ""

    # Count test assertions
    local total_assertions=$(grep -r "assert" "$TESTS_DIR" --include="test_*.sh" | wc -l | tr -d ' ')
    echo -e "Total Assertions: ${BLUE}$total_assertions${NC}"

    # Count test functions
    local total_test_functions=$(grep -r "^test_" "$TESTS_DIR" --include="test_*.sh" | wc -l | tr -d ' ')
    echo -e "Test Functions:   ${BLUE}$total_test_functions${NC}"

    # Count test files
    local total_test_files=$(find "$TESTS_DIR" -name 'test_*.sh' -type f ! -name 'test_utils.sh' | wc -l | tr -d ' ')
    echo -e "Test Files:       ${BLUE}$total_test_files${NC}"

    echo ""
}

# Cleanup function
cleanup() {
    echo -e "${CYAN}Cleaning up temporary files...${NC}"
    rm -f /tmp/test_*_output.log
    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"

    # Print header
    echo -e "${BLUE}"
    echo "========================================="
    echo "  TEST RUNNER"
    echo "  Claude Code Delegation System"
    echo "========================================="
    echo -e "${NC}"
    echo ""

    # Check prerequisites
    check_prerequisites

    # Run coverage analysis if requested
    if [[ $COVERAGE_MODE -eq 1 ]]; then
        run_coverage_analysis
        echo ""
    fi

    # Run all tests
    local exit_code=0
    run_all_tests || exit_code=$?

    # Cleanup
    cleanup

    exit $exit_code
}

# Trap exit for cleanup
trap cleanup EXIT

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
