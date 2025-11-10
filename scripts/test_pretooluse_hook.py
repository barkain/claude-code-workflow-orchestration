#!/usr/bin/env python3
"""Test the PreToolUse hook"""
import json
import subprocess
import sys

def test_hook():
    """Test the PreToolUse hook with sample data"""

    # Test case 1: File operation with relative path
    test_data = {
        "tool_name": "Read",
        "tool_args": {
            "file_path": "test.txt"
        }
    }

    result = run_hook(test_data)
    logger.info("Test 1 - File operation with relative path:")
    logger.info("Input: %s", json.dumps(test_data, indent=2))
    logger.info("Output: %s", json.dumps(result, indent=2))

    # Test case 2: Complex grep pattern
    test_data = {
        "tool_name": "Grep",
        "tool_args": {
            "pattern": "def\\s+\\w+\\(.*\\).*:.*# This is a very long and complex regex pattern that should trigger delegation"
        }
    }

    result = run_hook(test_data)
    logger.info("Test 2 - Complex grep pattern:")
    logger.info("Input: %s", json.dumps(test_data, indent=2))
    logger.info("Output: %s", json.dumps(result, indent=2))

    # Test case 3: Normal operation
    test_data = {
        "tool_name": "TodoWrite",
        "tool_args": {
            "todos": []
        }
    }

    result = run_hook(test_data)
    logger.info("Test 3 - Normal operation:")
    logger.info("Input: %s", json.dumps(test_data, indent=2))
    logger.info("Output: %s", json.dumps(result, indent=2))

def run_hook(test_data: dict) -> dict:
    """Run the hook with test data"""
    try:
        process = subprocess.run(
            ["python3", "scripts/pretooluse_hook.py"],
            input=json.dumps(test_data),
            text=True,
            capture_output=True,
            timeout=10
        )

        if process.returncode == 0:
            return json.loads(process.stdout)
        else:
            return {
                "error": "Hook failed",
                "stdout": process.stdout,
                "stderr": process.stderr,
                "returncode": process.returncode
            }

    except subprocess.TimeoutExpired:
        return {"error": "Hook timed out"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON output: {e}", "raw_output": process.stdout}
    except Exception as e:
        return {"error": f"Test failed: {e}"}

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)

    test_hook()