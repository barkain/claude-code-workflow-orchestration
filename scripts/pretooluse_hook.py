#!/usr/bin/env python3
"""
PreToolUse Hook for Claude Code
Entry point called by Claude Code's hook system
"""
import json
import logging
import os
import sys

# Configure logging for hook operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main hook entry point called by Claude Code"""
    try:
        # Read hook input from stdin (Claude Code passes data this way)
        hook_data = json.loads(sys.stdin.read())

        # Extract Claude Code hook data format
        tool_name = hook_data.get('tool_name', '')
        tool_input = hook_data.get('tool_input', {})
        session_id = hook_data.get('session_id', '')
        transcript_path = hook_data.get('transcript_path', '')
        cwd = hook_data.get('cwd', '')

        # Context-aware delegation logic
        result = analyze_and_delegate_with_context(
            tool_name, tool_input, session_id, transcript_path, cwd
        )

        # Output result for Claude Code
        sys.stdout.write(json.dumps(result))

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON input: %s", e)
        error_result = {
            "action": "continue",
            "error": f"JSON decode error: {e}"
        }
        sys.stdout.write(json.dumps(error_result))
        sys.exit(1)
    except (KeyError, ValueError) as e:
        logger.error("Invalid hook data: %s", e)
        error_result = {
            "action": "continue",
            "error": f"Invalid hook data: {e}"
        }
        sys.stdout.write(json.dumps(error_result))
        sys.exit(1)

def analyze_and_delegate_with_context(
    tool_name: str,
    tool_input: dict,
    session_id: str,
    transcript_path: str,
    cwd: str
) -> dict:
    """Analyze tool call with context and determine delegation"""

    # Log context for debugging (using session_id and cwd)
    logger.debug("Processing tool %s in session %s at %s", tool_name, session_id, cwd)

    # Get user context for potential future enhancements
    user_context = get_user_context(transcript_path) if transcript_path else {}

    # Context-aware behavior: Check if in development/testing mode
    is_development_context = (
        'test' in cwd.lower() or
        'debug' in user_context.get('last_user_message', '').lower()
    )

    # File operation safety checks with context awareness
    if tool_name in ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
        return handle_file_operations(tool_name, tool_input, is_development_context)

    # Complex analysis delegation
    if tool_name in ['Grep', 'Glob'] and is_complex_pattern(tool_input):
        return delegate_to_analysis_agent(tool_name, tool_input)

    # Default: continue with original tool call
    return {"action": "continue"}

def get_user_context(transcript_path: str) -> dict:
    """Extract user context from transcript for decision making"""
    try:
        if not os.path.exists(transcript_path):
            return {}

        # Read last few lines of transcript to understand context
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Get the last user message for context
        last_user_message = ""
        for line in reversed(lines[-10:]):  # Check last 10 lines
            try:
                entry = json.loads(line.strip())
                if entry.get('role') == 'user':
                    last_user_message = entry.get('content', '')
                    break
            except json.JSONDecodeError:
                continue

        return {
            "last_user_message": last_user_message,
            "session_length": len(lines)
        }

    except (OSError, IOError, json.JSONDecodeError) as e:
        logger.warning("Failed to read transcript context: %s", e)
        return {}

def handle_file_operations(tool_name: str, tool_args: dict, is_development_context: bool = False) -> dict:
    """Handle file operation delegations"""
    file_path = tool_args.get('file_path', '') or tool_args.get('notebook_path', '')

    if not file_path:
        return {"action": "continue"}

    # Convert relative to absolute paths
    if not os.path.isabs(file_path):
        abs_path = os.path.abspath(file_path)
        path_key = 'notebook_path' if 'notebook_path' in tool_args else 'file_path'
        return {
            "action": "modify",
            "modified_args": {**tool_args, path_key: abs_path}
        }

    # Block dangerous operations
    dangerous_paths = ['/etc', '/sys', '/proc', '/dev']
    if any(file_path.startswith(path) for path in dangerous_paths):
        return {
            "action": "block",
            "reason": f"Access to {file_path} is not allowed for {tool_name} operation"
        }

    # Tool-specific validations (context-aware)
    if tool_name == "Write" and os.path.exists(file_path):
        if is_development_context:
            logger.debug("Write operation will overwrite existing file (dev context): %s", file_path)
        else:
            logger.info("Write operation will overwrite existing file: %s", file_path)

    elif tool_name == "Read" and not os.path.exists(file_path):
        logger.warning("Read operation on non-existent file: %s", file_path)
        # Let the tool handle the error naturally

    elif tool_name in ["Edit", "MultiEdit"] and not os.path.exists(file_path):
        if is_development_context:
            # More lenient in development context - let the tool handle it
            logger.warning("Edit operation on non-existent file (dev context): %s", file_path)
        else:
            return {
                "action": "block",
                "reason": f"Cannot edit non-existent file: {file_path}"
            }

    return {"action": "continue"}

def is_complex_pattern(tool_args: dict) -> bool:
    """Determine if search pattern is complex enough to delegate"""
    pattern = tool_args.get('pattern', '')

    if not pattern:
        return False

    complexity_score = calculate_pattern_complexity(pattern, tool_args)
    return complexity_score >= 60  # Threshold for delegation

def calculate_pattern_complexity(pattern: str, tool_args: dict) -> int:
    """Calculate comprehensive pattern complexity score (0-100)"""
    score = 0

    # Base complexity factors
    base_factors = [
        (len(pattern) > 50, 15, "Long pattern"),
        (len(pattern) > 100, 10, "Very long pattern"),
        (pattern.count('(') > 2, 20, "Multiple capture groups"),
        (pattern.count('[') > 1, 15, "Multiple character classes"),
        ('|' in pattern, 10, "Alternation operator"),
    ]

    # Advanced regex features
    advanced_features = [
        (r'(?=' in pattern or r'(?!' in pattern, 25, "Lookahead assertions"),
        (r'(?<=' in pattern or r'(?<!' in pattern, 25, "Lookbehind assertions"),
        (r'\b' in pattern or r'\B' in pattern, 10, "Word boundaries"),
        (r'\d+' in pattern or r'\w+' in pattern, 5, "Quantified shortcuts"),
        (pattern.count('*') + pattern.count('+') > 3, 15, "Multiple quantifiers"),
        (r'\..*\.' in pattern, 12, "Greedy dot matching"),
        (pattern.count('\\') > 5, 10, "Heavy escaping"),
    ]

    # Contextual complexity
    contextual_factors = [
        ('multiline' in tool_args.get('flags', ''), 8, "Multiline mode"),
        ('recursive' in str(tool_args.get('glob', '')), 12, "Recursive search"),
        (tool_args.get('type') in ['py', 'js', 'ts', 'go'], 5, "Code file search"),
        (len(str(tool_args.get('path', '')).split('/')) > 5, 8, "Deep path search"),
    ]

    # Anti-patterns that reduce complexity
    simplifying_factors = [
        (pattern.isalnum(), -10, "Simple alphanumeric"),
        (len(pattern) < 10 and pattern.count('\\') == 0, -8, "Short simple pattern"),
        (pattern in ['TODO', 'FIXME', 'BUG', 'HACK'], -15, "Common search terms"),
    ]

    # Calculate score with explanations
    explanations = []

    for condition, points, explanation in base_factors + advanced_features + contextual_factors:
        if condition:
            score += points
            explanations.append(f"+{points}: {explanation}")

    for condition, points, explanation in simplifying_factors:
        if condition:
            score += points  # points are negative
            explanations.append(f"{points}: {explanation}")

    # Log complexity analysis for debugging
    if score >= 40:  # Log significant complexity
        logger.debug("Pattern complexity analysis: %d points", score)
        for explanation in explanations[:3]:  # Top 3 factors
            logger.debug("  %s", explanation)

    return max(0, min(100, score))  # Clamp to 0-100 range

def delegate_to_analysis_agent(tool_name: str, tool_args: dict) -> dict:
    """Delegate complex analysis to subagent"""
    return {
        "action": "delegate",
        "agent_type": "general-purpose",
        "task_description": f"Perform {tool_name} operation with complex pattern analysis",
        "tool_name": tool_name,
        "tool_args": tool_args
    }

if __name__ == "__main__":
    main()