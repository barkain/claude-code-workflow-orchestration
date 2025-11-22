#!/bin/bash

# Test script for phase-validator.md validation rules
# Tests: execute_file_exists_rule and execute_content_match_rule implementations

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test setup
TEST_DIR="/tmp/phase_validator_tests_$$"
AGENT_FILE="/Users/nadavbarkai/dev/claude-code-delegation-system/agents/phase-validator.md"

# Cleanup function
cleanup() {
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Setup test environment
setup() {
    mkdir -p "$TEST_DIR"
    echo "Test content for validation" > "$TEST_DIR/test_file.txt"
    echo "Case Sensitive Content" > "$TEST_DIR/case_test.txt"
    echo "Multiple matches test test test test" > "$TEST_DIR/multi_match.txt"
    echo "" > "$TEST_DIR/empty_file.txt"
    mkdir -p "$TEST_DIR/test_directory"
}

# Test assertion helper
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        echo -e "  Expected: $expected"
        echo -e "  Actual:   $actual"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Test assertion for JSON field
assert_json_field() {
    local json="$1"
    local field="$2"
    local expected="$3"
    local test_name="$4"

    local actual=$(echo "$json" | jq -r ".$field")

    assert_equals "$expected" "$actual" "$test_name"
}

# Test assertion for boolean JSON field
assert_json_boolean() {
    local json="$1"
    local field="$2"
    local expected="$3"
    local test_name="$4"

    local actual=$(echo "$json" | jq -r ".$field")

    assert_equals "$expected" "$actual" "$test_name"
}

# Extract and source validation functions from agent file
source_validation_functions() {
    # Extract execute_file_exists_rule function
    awk '/^execute_file_exists_rule\(\) \{$/,/^}$/{print}' "$AGENT_FILE" | sed '/^```/d' > /tmp/file_exists_func.sh

    # Extract execute_content_match_rule function
    awk '/^execute_content_match_rule\(\) \{$/,/^}$/{print}' "$AGENT_FILE" | sed '/^```/d' > /tmp/content_match_func.sh

    # Source the functions
    source /tmp/file_exists_func.sh
    source /tmp/content_match_func.sh

    # Cleanup temp files
    rm -f /tmp/file_exists_func.sh /tmp/content_match_func.sh
}

# Test 1: file_exists with existing file returns passed
test_file_exists_with_existing_file() {
    local config="{\"path\": \"$TEST_DIR/test_file.txt\", \"type\": \"file\"}"
    local result=$(execute_file_exists_rule "$config")

    assert_json_field "$result" "status" "passed" "file_exists: existing file returns passed"
    assert_json_boolean "$result" "details.exists" "true" "file_exists: exists field is true"
    assert_json_field "$result" "details.actual_type" "file" "file_exists: actual_type is file"
}

# Test 2: file_exists with missing file returns failed
test_file_exists_with_missing_file() {
    local config="{\"path\": \"$TEST_DIR/nonexistent.txt\", \"type\": \"file\"}"
    local result=$(execute_file_exists_rule "$config" 2>&1)

    assert_json_field "$result" "status" "failed" "file_exists: missing file returns failed"
    assert_json_boolean "$result" "details.exists" "false" "file_exists: exists field is false"
}

# Test 3: file_exists handles missing path parameter
test_file_exists_missing_parameter() {
    local config="{\"type\": \"file\"}"
    local result=$(execute_file_exists_rule "$config" 2>&1)

    assert_json_field "$result" "status" "failed" "file_exists: missing path returns failed"
}

# Test 4: file_exists validates type matching (file vs directory)
test_file_exists_type_validation() {
    # Test file type matches file
    local config="{\"path\": \"$TEST_DIR/test_file.txt\", \"type\": \"file\"}"
    local result=$(execute_file_exists_rule "$config")
    assert_json_field "$result" "status" "passed" "file_exists: file type matches regular file"

    # Test directory type matches directory
    config="{\"path\": \"$TEST_DIR/test_directory\", \"type\": \"directory\"}"
    result=$(execute_file_exists_rule "$config")
    assert_json_field "$result" "status" "passed" "file_exists: directory type matches directory"

    # Test file type doesn't match directory
    config="{\"path\": \"$TEST_DIR/test_directory\", \"type\": \"file\"}"
    result=$(execute_file_exists_rule "$config")
    assert_json_field "$result" "status" "failed" "file_exists: directory doesn't match file type"
}

# Test 5: content_match finds exact string patterns (literal match_type)
test_content_match_literal() {
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"pattern\": \"Test content\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: literal match finds exact string"
    assert_json_boolean "$result" "details.matched" "true" "content_match: matched field is true"
}

# Test 6: content_match finds regex patterns
test_content_match_regex() {
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"pattern\": \"Test.*validation\", \"match_type\": \"regex\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: regex match finds pattern"
}

# Test 7: content_match handles missing file
test_content_match_missing_file() {
    local config="{\"file_path\": \"$TEST_DIR/nonexistent.txt\", \"pattern\": \"test\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config" 2>&1)

    assert_json_field "$result" "status" "failed" "content_match: missing file returns failed"
    assert_json_boolean "$result" "details.matched" "false" "content_match: matched field is false for missing file"
}

# Test 8: content_match handles missing pattern parameter
test_content_match_missing_pattern() {
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config" 2>&1)

    assert_json_field "$result" "status" "failed" "content_match: missing pattern returns failed"
}

# Test 9: content_match case-sensitive vs case-insensitive
test_content_match_case_sensitivity() {
    # Case-sensitive: should fail to match
    local config="{\"file_path\": \"$TEST_DIR/case_test.txt\", \"pattern\": \"case sensitive\", \"match_type\": \"literal\", \"case_sensitive\": true}"
    local result=$(execute_content_match_rule "$config")
    assert_json_field "$result" "status" "failed" "content_match: case-sensitive doesn't match different case"

    # Case-insensitive: should match
    config="{\"file_path\": \"$TEST_DIR/case_test.txt\", \"pattern\": \"case sensitive\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    result=$(execute_content_match_rule "$config")
    assert_json_field "$result" "status" "passed" "content_match: case-insensitive matches different case"
}

# Test 10: content_match counts matches correctly
test_content_match_count() {
    local config="{\"file_path\": \"$TEST_DIR/multi_match.txt\", \"pattern\": \"test\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: multiple matches return passed"

    local match_count=$(echo "$result" | jq -r '.details.match_count')
    assert_equals "4" "$match_count" "content_match: counts 4 occurrences correctly"
}

# Test 11: file_exists with any type
test_file_exists_any_type() {
    # File should match 'any' type
    local config="{\"path\": \"$TEST_DIR/test_file.txt\", \"type\": \"any\"}"
    local result=$(execute_file_exists_rule "$config")
    assert_json_field "$result" "status" "passed" "file_exists: file matches 'any' type"

    # Directory should match 'any' type
    config="{\"path\": \"$TEST_DIR/test_directory\", \"type\": \"any\"}"
    result=$(execute_file_exists_rule "$config")
    assert_json_field "$result" "status" "passed" "file_exists: directory matches 'any' type"
}

# Test 12: content_match with contains match_type
test_content_match_contains() {
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"pattern\": \"content\", \"match_type\": \"contains\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: contains match finds substring"
}

# Test 13: content_match with empty file
test_content_match_empty_file() {
    local config="{\"file_path\": \"$TEST_DIR/empty_file.txt\", \"pattern\": \"test\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "failed" "content_match: empty file returns failed (no matches)"

    local match_count=$(echo "$result" | jq -r '.details.match_count')
    assert_equals "0" "$match_count" "content_match: empty file has 0 matches"
}

# Test 14: file_exists JSON structure validation
test_file_exists_json_structure() {
    local config="{\"path\": \"$TEST_DIR/test_file.txt\", \"type\": \"file\"}"
    local result=$(execute_file_exists_rule "$config")

    # Validate JSON structure
    if echo "$result" | jq -e '.status' >/dev/null 2>&1 && \
       echo "$result" | jq -e '.message' >/dev/null 2>&1 && \
       echo "$result" | jq -e '.details' >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}: file_exists: JSON structure contains required fields"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: file_exists: JSON structure missing required fields"
        echo -e "  Result: $result"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Test 15: content_match JSON structure validation
test_content_match_json_structure() {
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"pattern\": \"test\", \"match_type\": \"literal\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    # Validate JSON structure
    if echo "$result" | jq -e '.status' >/dev/null 2>&1 && \
       echo "$result" | jq -e '.message' >/dev/null 2>&1 && \
       echo "$result" | jq -e '.details.match_count' >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}: content_match: JSON structure contains required fields"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: content_match: JSON structure missing required fields"
        echo -e "  Result: $result"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Test 16: file_exists with default type parameter
test_file_exists_default_type() {
    # When type is omitted, it should default to "any"
    local config="{\"path\": \"$TEST_DIR/test_file.txt\"}"
    local result=$(execute_file_exists_rule "$config")

    assert_json_field "$result" "status" "passed" "file_exists: defaults to 'any' type when type omitted"
}

# Test 17: content_match with default match_type
test_content_match_default_match_type() {
    # When match_type is omitted, it should default to "contains"
    local config="{\"file_path\": \"$TEST_DIR/test_file.txt\", \"pattern\": \"content\", \"case_sensitive\": false}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: defaults to 'contains' match type when omitted"
}

# Test 18: content_match with default case_sensitive
test_content_match_default_case_sensitive() {
    # When case_sensitive is omitted, it should default to true
    local config="{\"file_path\": \"$TEST_DIR/case_test.txt\", \"pattern\": \"Case Sensitive\", \"match_type\": \"literal\"}"
    local result=$(execute_content_match_rule "$config")

    assert_json_field "$result" "status" "passed" "content_match: defaults to case-sensitive when omitted"
}

# Main test execution
main() {
    echo "=========================================="
    echo "Phase Validator - Validation Rules Tests"
    echo "=========================================="
    echo ""

    setup
    source_validation_functions

    echo "Running file_exists tests..."
    test_file_exists_with_existing_file
    test_file_exists_with_missing_file
    test_file_exists_missing_parameter
    test_file_exists_type_validation
    test_file_exists_any_type
    test_file_exists_default_type
    test_file_exists_json_structure

    echo ""
    echo "Running content_match tests..."
    test_content_match_literal
    test_content_match_regex
    test_content_match_missing_file
    test_content_match_missing_pattern
    test_content_match_case_sensitivity
    test_content_match_count
    test_content_match_contains
    test_content_match_empty_file
    test_content_match_default_match_type
    test_content_match_default_case_sensitive
    test_content_match_json_structure

    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo "Total Tests:  $TOTAL_TESTS"
    echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"

    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
        echo ""
        echo "Some tests failed. Please review the output above."
        exit 1
    else
        echo -e "${GREEN}Failed:       $FAILED_TESTS${NC}"
        echo ""
        echo -e "${GREEN}All tests passed successfully!${NC}"
        exit 0
    fi
}

# Run main function
main
