#!/bin/bash
# Activate orchestration mode for current session

echo "🎯 Activating Orchestration Mode..."

# Set the orchestration flag
export ORCHESTRATION_MODE="active"

# Initialize session tracking
export SESSION_ID="orch_$(date +%Y%m%d_%H%M%S)"
export DELEGATION_COUNT="0"

echo "✅ Orchestration mode activated!"
echo "   Session ID: $SESSION_ID"
echo ""
echo "When orchestration mode is active:"
echo "  • Main agent can only use: Task, TodoWrite, Read, Grep, Glob, SlashCommand"
echo "  • All implementation work must be delegated via Task tool"
echo "  • Environment variables persist across hook invocations"
echo "  • Use 'export ORCHESTRATION_MODE=' to deactivate"
echo ""
echo "To share context with subagents, set environment variables:"
echo "  export TASK_CONTEXT='specific requirements'"
echo "  export FOCUS_AREA='what to focus on'"