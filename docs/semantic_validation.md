# Semantic Validation Implementation

## Overview

Semantic validation is an intelligent validation layer implemented in the `validation_gate.sh` PostToolUse hook. It uses Claude Haiku to compare task objectives with subagent deliverables to determine if a delegated task was successfully completed.

## Architecture

### Validation Flow

```
PostToolUse Hook Triggered
         ↓
Read stdin JSON (tool info)
         ↓
Detect validation trigger
         ↓
Try semantic validation FIRST
         ↓
    ┌─────────────┐
    │ Semantic    │
    │ Validation  │
    └─────────────┘
         ↓
    ┌─────────────────────────────┐
    │ PASSED/FAILED/NOT_APPLICABLE│
    └─────────────────────────────┘
         ↓
    ┌────────┴────────┐
    │                 │
PASSED/FAILED    NOT_APPLICABLE
    │                 │
Persist result   Fall back to
    │            rule-based
    ↓            validation
Evaluate             ↓
blocking         Config file
rules            validation
    │                 │
    └────────┬────────┘
             ↓
    Block or allow
    workflow execution
```

## Implementation Details

### Key Components

#### 1. `semantic_validation()` Function

**Location:** `/Users/nadavbarkai/dev/claude-code-workflow-orchestration/hooks/PostToolUse/validation_gate.sh` (lines 307-503)

**Purpose:** Compare task objectives with subagent deliverables using AI

**Parameters:**
- `$1`: Full JSON input from hook system containing:
  - `tool.name`: Tool that was invoked (e.g., "Task", "SubagentTask", "AgentTask")
  - `tool.parameters.prompt`: Task objective/description
  - `tool.result`: Subagent's deliverables/output
  - `sessionId`: Session identifier
  - `workflowId`: Workflow identifier (optional)

**Output Format:**
```
SEMANTIC_VALIDATION|STATUS|message
```

Where STATUS is one of:
- `PASSED`: Task objective was met
- `FAILED`: Task objective was not met
- `NOT_APPLICABLE`: Semantic validation cannot be performed (falls back to rule-based)

**Return Codes:**
- `0`: Validation passed OR not applicable (fail-open)
- `1`: Validation failed (blocks workflow if blocking rules enabled)

#### 2. Haiku Validation Prompt

The semantic validation function constructs a structured prompt for Claude Haiku:

```
You are a validation checker comparing task objectives with actual deliverables.

TASK OBJECTIVE:
[extracted from tool.parameters.prompt]

SUBAGENT DELIVERABLES:
[extracted from tool.result]

QUESTION: Did the subagent accomplish the task objective?

Analyze:
1. Does the deliverable address the stated objective?
2. Are key requirements mentioned in objective present in deliverable?
3. Are there any obvious gaps or missing elements?

Return ONLY valid JSON (no markdown, no code fences):
{
  "status": "PASSED" or "FAILED",
  "reasoning": "brief explanation of why it passed or failed",
  "confidence": 0.0 to 1.0
}
```

#### 3. Response Parsing

The function includes robust JSON parsing that handles:
- Pure JSON responses
- JSON wrapped in markdown code fences (```json ... ```)
- Missing or invalid status fields (returns NOT_APPLICABLE)
- Status normalization (converts lowercase to uppercase)

#### 4. Integration with Main Hook Logic

**Modified `main()` function** (lines 755-940):

The main hook logic now:
1. **Reads stdin once** and stores for reuse (prevents stdin consumption issues)
2. **Tries semantic validation first** for all TRIGGER events
3. **Parses semantic result** and branches based on status:
   - `PASSED`/`FAILED`: Use semantic result, persist state, evaluate blocking rules
   - `NOT_APPLICABLE`: Fall back to rule-based validation with config files
4. **Persists semantic results** using existing `persist_validation_state()` function
5. **Evaluates blocking rules** consistently for both semantic and rule-based validation

## Validation Triggering

### When Semantic Validation Applies

Semantic validation is attempted for:
- **Tool names:** `Task`, `SubagentTask`, `AgentTask`
- **With parameters:** Non-empty `tool.parameters.prompt` field
- **With results:** Non-empty `tool.result` field

### When Semantic Validation Falls Back

Returns `NOT_APPLICABLE` and falls back to rule-based validation when:
- Tool is not a delegation tool (e.g., `TodoWrite`, `AskUserQuestion`)
- No task objective found in `tool.parameters.prompt`
- No tool result available in `tool.result`
- Claude command not available
- Haiku invocation fails (exit code ≠ 0)
- Invalid response format from Haiku

## State Persistence

### Semantic Validation State Schema

When semantic validation produces a result, it's persisted to:
```
.claude/state/validation/phase_semantic_{tool_name}_{session_id}_validation.json
```

**State structure:**
```json
{
  "workflow_id": "test_workflow_456",
  "phase_id": "semantic_Task_test_ses",
  "session_id": "test_session_123",
  "validation_status": "PASSED",
  "persisted_at": "2025-11-17T17:32:15Z",
  "summary": {
    "total_rules_executed": 1,
    "results_count": 1
  },
  "rule_results": [
    {
      "result_id": "semantic_validation_2025-11-17T17:32:15Z",
      "rule_id": "semantic_objective_match",
      "rule_type": "semantic",
      "validated_at": "2025-11-17T17:32:15Z",
      "status": "passed",
      "message": "The deliverable addresses the stated objective... (confidence: 0.95)",
      "details": {
        "validation_type": "semantic",
        "model": "haiku"
      }
    }
  ]
}
```

### Blocking Evaluation

After persisting semantic validation results, the hook evaluates blocking rules:

1. **Read validation state** for the workflow/phase
2. **Check validation_status**:
   - `FAILED` → Return 1 (block workflow execution)
   - `PASSED` → Return 0 (allow continuation)
   - `UNKNOWN` → Return 0 (fail-open, allow continuation)
3. **Exit hook** with appropriate code:
   - Exit 0: Allow workflow to continue
   - Exit 1: Block subsequent tool executions

## Error Handling

### Fail-Open Philosophy

Semantic validation follows a **fail-open** approach:
- All errors return `NOT_APPLICABLE` with return code 0
- Falls back to rule-based validation gracefully
- Never blocks workflow due to semantic validation errors

### Error Cases Handled

1. **Missing claude command**: Returns NOT_APPLICABLE, logs SKIP
2. **Haiku invocation failure**: Returns NOT_APPLICABLE, logs ERROR
3. **Invalid JSON response**: Returns NOT_APPLICABLE, logs ERROR
4. **Missing status field**: Returns NOT_APPLICABLE, logs ERROR
5. **Invalid status value**: Returns NOT_APPLICABLE, logs ERROR
6. **Timeout**: Handled by timeout command (60 seconds)

## Performance Considerations

### Optimization Strategies

1. **Input truncation**: Limits task objective and result to 10,000 characters each
   - Prevents token overflow
   - Keeps prompts small for faster Haiku responses
   - Adds "[truncated]" suffix when truncation occurs

2. **Timeout protection**: 60-second timeout for Haiku invocation
   - Prevents infinite hangs
   - Uses `timeout` (Linux) or `gtimeout` (macOS)
   - Gracefully degrades if timeout command unavailable

3. **Minimal logging**: Only essential events logged
   - VALIDATION: Semantic validation start/result
   - SKIP: When semantic validation not applicable
   - ERROR: When Haiku invocation or parsing fails

### Expected Performance

- **Semantic validation**: 2-10 seconds (Haiku API call)
- **Fallback to rule-based**: Immediate (no API call)
- **Total overhead**: <1 second for most non-API operations

## Logging

### Log Events

All semantic validation events are logged to:
```
.claude/state/validation/gate_invocations.log
```

**Log format:**
```
[TIMESTAMP] [EVENT_TYPE] [COMPONENT] [DETAILS]
```

**Example log entries:**
```
[2025-11-17T17:32:02Z] [VALIDATION] [semantic_validation] Invoking Haiku for semantic validation (objective length: 58, result length: 181)
[2025-11-17T17:32:10Z] [VALIDATION] [semantic_validation] PASSED: The deliverable addresses the stated objective (confidence: 0.95)
[2025-11-17T17:32:10Z] [VALIDATION] [gate] Semantic validation returned PASSED: The deliverable addresses the stated objective (confidence: 0.95)
[2025-11-17T17:32:10Z] [DEBUG] [gate] Evaluating blocking rules for semantic validation (workflow: test_workflow_456, phase: semantic_Task_test_ses, status: PASSED)
[2025-11-17T17:32:10Z] [VALIDATION] [gate] Semantic validation PASSED - workflow may continue (blocking: allow)
```

## Testing

### Unit Testing

To test semantic validation without making API calls, you can:

1. **Mock the claude command**:
```bash
# Create a mock claude script
cat > /tmp/mock_claude.sh << 'EOF'
#!/bin/bash
echo '{"status": "PASSED", "reasoning": "Mock validation passed", "confidence": 1.0}'
EOF
chmod +x /tmp/mock_claude.sh

# Add to PATH
export PATH="/tmp:$PATH"
```

2. **Source the validation_gate.sh script**:
```bash
source /Users/nadavbarkai/dev/claude-code-workflow-orchestration/hooks/PostToolUse/validation_gate.sh
```

3. **Test with sample inputs**:
```bash
test_input='{
  "tool": {
    "name": "Task",
    "parameters": {
      "prompt": "Create a calculator module"
    },
    "result": "Created calculator.py with add() and subtract() functions"
  },
  "sessionId": "test_123",
  "workflowId": "wf_456"
}'

result=$(semantic_validation "${test_input}")
echo "Result: ${result}"
```

### Integration Testing

To test the full validation flow:

1. **Enable debug logging**:
```bash
export DEBUG_DELEGATION_HOOK=1
```

2. **Create a test validation config**:
```bash
mkdir -p .claude/state/validation
cat > .claude/state/validation/phase_test_workflow_test_phase_validation.json << 'EOF'
{
  "metadata": {
    "workflow_id": "test_workflow",
    "phase_id": "test_phase"
  },
  "rules": []
}
EOF
```

3. **Trigger the hook with test input**:
```bash
echo '{
  "tool": {
    "name": "Task",
    "parameters": {
      "prompt": "Create a test file"
    },
    "result": "Created test.txt"
  },
  "sessionId": "test_session",
  "workflowId": "test_workflow"
}' | /Users/nadavbarkai/dev/claude-code-workflow-orchestration/hooks/PostToolUse/validation_gate.sh
```

4. **Check logs and state**:
```bash
# View logs
tail -20 .claude/state/validation/gate_invocations.log

# View persisted state
cat .claude/state/validation/phase_semantic_Task_test_ses_validation.json
```

## Configuration

### Environment Variables

No additional environment variables are required. Semantic validation uses the same environment as the existing validation system:

- `DEBUG_DELEGATION_HOOK`: Enable debug logging (optional)
- `CLAUDE_PROJECT_DIR`: Project directory for state files (defaults to PWD)

### Feature Flags

Currently, semantic validation is always enabled when:
1. Tool is a delegation tool (Task/SubagentTask/AgentTask)
2. Task objective and result are present
3. Claude command is available

To disable semantic validation and use only rule-based validation:
- Remove or comment out the semantic validation function call in main()
- OR modify the function to always return NOT_APPLICABLE

## Future Enhancements

### Potential Improvements

1. **Confidence thresholding**: Block workflow if confidence < 0.7
2. **Model selection**: Use Opus for complex validations, Haiku for simple ones
3. **Caching**: Cache validation results for identical objective/deliverable pairs
4. **Retry logic**: Retry failed Haiku invocations with exponential backoff
5. **Hybrid validation**: Combine semantic + rule-based results
6. **Custom prompts**: Allow customization of validation prompt per workflow

## Troubleshooting

### Common Issues

#### Issue: Semantic validation always returns NOT_APPLICABLE

**Symptoms:**
- All semantic validations fall back to rule-based validation
- Logs show "Semantic validation not applicable"

**Diagnosis:**
```bash
# Check if tool is delegation tool
# Check if prompt field exists
# Check if result field exists

# View recent logs
tail -50 .claude/state/validation/gate_invocations.log | grep semantic
```

**Solutions:**
- Ensure tool.parameters.prompt is populated
- Ensure tool.result is populated
- Verify tool name is Task/SubagentTask/AgentTask

#### Issue: Haiku invocation fails

**Symptoms:**
- Logs show "Haiku invocation failed with exit code X"
- Semantic validation returns NOT_APPLICABLE

**Diagnosis:**
```bash
# Test claude command manually
claude --model haiku -p "Test prompt"

# Check claude is in PATH
which claude

# Check API key configuration
# (claude command configuration specific to your setup)
```

**Solutions:**
- Verify claude command is installed and in PATH
- Check API credentials are configured
- Ensure network connectivity

#### Issue: Invalid JSON response from Haiku

**Symptoms:**
- Logs show "Invalid Haiku response format"
- Semantic validation returns NOT_APPLICABLE

**Diagnosis:**
```bash
# Run validation manually and inspect Haiku output
# Check if response is wrapped in markdown code fences
```

**Solutions:**
- The function already handles markdown code fences
- If issue persists, check Haiku prompt instructions
- May need to adjust JSON extraction logic

## Implementation Summary

### Files Modified

1. **`/Users/nadavbarkai/dev/claude-code-workflow-orchestration/hooks/PostToolUse/validation_gate.sh`**
   - Added `semantic_validation()` function (lines 307-503)
   - Modified `main()` function to integrate semantic validation (lines 755-940)
   - Total additions: ~250 lines of code

### Key Features

- **AI-powered validation**: Uses Claude Haiku to semantically compare objectives vs deliverables
- **Fail-safe design**: Falls back to rule-based validation on any error
- **State persistence**: Stores semantic validation results in same format as rule-based validation
- **Blocking support**: Can block workflow execution if semantic validation fails
- **Comprehensive logging**: All operations logged for debugging and audit
- **Performance optimized**: Input truncation and timeouts prevent resource exhaustion

### Integration Points

- **PostToolUse hook**: Triggered after every tool execution
- **State persistence**: Uses existing `persist_validation_state()` function
- **Blocking evaluation**: Uses existing `evaluate_blocking_rules()` function
- **Logging**: Uses existing `log_event()` function

## Conclusion

Semantic validation enhances the delegation system with intelligent, AI-powered validation of task completion. By comparing task objectives with subagent deliverables, it provides a more nuanced and flexible validation mechanism than rule-based validation alone. The fail-open design ensures robustness, while the integration with existing validation infrastructure provides a seamless experience.
