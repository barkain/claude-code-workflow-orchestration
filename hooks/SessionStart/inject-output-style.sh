#!/usr/bin/env bash

# Output the technical-adaptive as additionalContext

# Read and JSON-escape the markdown content
ESCAPED_CONTENT=$(jq -Rs '.' "${CLAUDE_PLUGIN_ROOT}/output-styles/technical-adaptive.md")

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${ESCAPED_CONTENT}
  }
}
EOF

exit 0
