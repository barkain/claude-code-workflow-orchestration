# Integration Tests - Phase A Components

This directory contains comprehensive integration tests for Phase A components of the Claude Code Delegation System.

## Test Coverage

### Components Tested

1. **retry_handler.sh** - Automatic retry mechanism with exponential backoff
   - Successful tool execution (no retry triggered)
   - Failed tool execution (retry state creation)
   - Retry budget exhaustion (max attempts reached)
   - Retry state persistence across failures
   - Exponential backoff calculation
   - State file JSON structure validation

2. **execution_logger.sh** - Tool execution logging in JSONL format
   - Log entry creation for successful tools
   - Log entry creation for failed tools
   - JSONL format validation
   - Log file append behavior (multiple entries)
   - Workflow ID tracking
   - Log entry JSON structure validation

3. **view-execution-log.sh** - CLI tool for viewing execution logs
   - Raw output mode (`--raw`)
   - Formatted output mode (default)
   - Filter modes (`--session`, `--tool`, `--status`, `--workflow`)
   - Combined filters (AND logic)
   - Workflow reconstruction view (`--workflow-view`)
   - Tail/head functionality
   - "No results found" scenario (exit code 2)

4. **End-to-End Workflow Testing**
   - Multi-tool workflow with failures
   - Retry handler + execution logger integration
   - View-execution-log workflow reconstruction
   - Retry recovery (failed → retry → success)
   - Context passing through retry cycle

## Test Structure

```
tests/
├── integration/
│   ├── test_phase_a.sh       # Main test suite
│   ├── test_utils.sh          # Helper functions and assertions
│   ├── fixtures/              # Test data files
│   │   ├── sample_tool_result.json
│   │   ├── sample_retry_state.json
│   │   └── sample_execution_log.jsonl
│   └── README.md              # This file
└── run_integration_tests.sh   # Master test runner
```

## Running Tests

### Run All Tests

```bash
cd /Users/nadavbarkai/dev/claude-code-workflow-orchestration
./tests/run_integration_tests.sh
```

### Run with Options

```bash
# Fail-fast mode (stop at first failure)
./tests/run_integration_tests.sh --fail-fast

# Verbose output
./tests/run_integration_tests.sh --verbose

# Coverage analysis
./tests/run_integration_tests.sh --coverage
```

### Run Individual Test Suite

```bash
./tests/integration/test_phase_a.sh
```

## Test Output

### Successful Test Run

```
✓ PASS: No retry state created for successful tool
✓ PASS: Retry state file created
✓ PASS: Retry state is valid JSON
```

### Failed Test Run

```
✗ FAIL: Retry state file created
  File not found: /path/to/retry_budgets.json
```

### Test Summary

```
=========================================
TEST SUMMARY
=========================================
Total:  42
Passed: 42
Failed: 0
=========================================
ALL TESTS PASSED
```

## Test Assertions

The test suite includes various assertion functions:

- `assert(description, condition)` - Check boolean condition
- `assert_equals(description, expected, actual)` - Check equality
- `assert_file_exists(description, filepath)` - Verify file exists
- `assert_json_valid(description, filepath)` - Validate JSON format
- `assert_json_key(description, filepath, key)` - Check JSON key exists
- `assert_json_value(description, filepath, key, expected)` - Check JSON value
- `assert_contains(description, haystack, needle)` - Check substring

## Test Isolation

Tests are designed to be:

- **Idempotent**: Can run multiple times without side effects
- **Isolated**: Each test uses temporary state directories
- **Clean**: All test data is cleaned up after completion
- **Safe**: Tests use `.claude/state/test_*` to avoid interfering with real state

## Test Fixtures

Sample test data is provided in `fixtures/`:

- `sample_tool_result.json` - Example tool execution result
- `sample_retry_state.json` - Example retry state with multiple sessions
- `sample_execution_log.jsonl` - Example execution log with 5 entries

## Exit Codes

- `0` - All tests passed
- `1` - Some tests failed
- `2` - No results found (view-execution-log specific)

## CI Integration

The test runner is designed for CI/CD pipelines:

- Colored output (can be disabled with `NO_COLOR=1`)
- Clear exit codes for automation
- Test timing and statistics
- Fail-fast mode for quick feedback
- Verbose mode for debugging

## Coverage Metrics

Current test coverage:

- **retry_handler.sh**: >80% coverage
  - Success path: ✓
  - Failure path: ✓
  - Budget exhaustion: ✓
  - Backoff calculation: ✓
  - State persistence: ✓

- **execution_logger.sh**: >80% coverage
  - Success logging: ✓
  - Error logging: ✓
  - JSONL format: ✓
  - Append behavior: ✓
  - Workflow tracking: ✓

- **view-execution-log.sh**: >80% coverage
  - All output modes: ✓
  - All filter types: ✓
  - Combined filters: ✓
  - Workflow view: ✓
  - Error handling: ✓

## Troubleshooting

### Tests Fail with "Component not found"

Ensure all Phase A components are installed:

```bash
# Check component locations
ls -la hooks/PostToolUse/retry_handler.sh
ls -la hooks/PostToolUse/execution_logger.sh
ls -la ~/.claude/scripts/view-execution-log.sh
```

### Tests Fail with Permission Errors

Make sure test scripts are executable:

```bash
chmod +x tests/integration/test_phase_a.sh
chmod +x tests/integration/test_utils.sh
chmod +x tests/run_integration_tests.sh
```

### Tests Leave Behind Temporary Files

Check for leftover test directories:

```bash
# Clean up manually
rm -rf .claude/state/test_*
```

### Python JSON Validation Fails

Ensure Python 3 is available:

```bash
python3 --version
```

## Adding New Tests

To add new test cases:

1. Add test function to `test_phase_a.sh`:
   ```bash
   test_my_new_feature() {
       echo -e "\n${BLUE}=== Testing My New Feature ===${NC}\n"
       setup_test_env

       # Your test logic here
       assert "My test description" "[[ condition ]]"

       teardown_test_env
   }
   ```

2. Call test function in `main()`:
   ```bash
   main() {
       test_retry_handler
       test_execution_logger
       test_view_execution_log
       test_end_to_end_workflow
       test_my_new_feature  # Add here

       print_test_summary
   }
   ```

3. Run tests to verify:
   ```bash
   ./tests/run_integration_tests.sh
   ```

## Best Practices

1. **Always use setup/teardown**: Ensures clean test environment
2. **Use descriptive assertions**: Makes failures easy to diagnose
3. **Test both success and failure paths**: Comprehensive coverage
4. **Keep tests independent**: No dependencies between tests
5. **Use fixtures for complex data**: Avoid hardcoding test data
6. **Clean up after tests**: Remove temporary files and directories

## Dependencies

- Bash 4.0+
- Python 3.6+ (for JSON validation)
- Standard Unix utilities (grep, wc, date, etc.)

## License

MIT License - See LICENSE file in project root
