---
description: Add statusline configuration to Claude settings file
argument-hint: ""
allowed-tools: Task, AskUserQuestion
---

# Add StatusLine Configuration

Adds the statusline configuration to a Claude settings file.

## Step 1: Ask Scope

Use AskUserQuestion to ask which settings file:
- **user**: `~/.claude/settings.json`
- **project**: `./.claude/settings.json`
- **local**: `./.claude/settings.local.json`

## Step 2: Execute via Task

Spawn a subagent with the Task tool using this prompt (replace [FILE_PATH] with resolved path):

```
Add statusline to settings file at [FILE_PATH].

1. Read the file. If not found → respond "NOT_FOUND" and stop
2. Parse JSON. If invalid → respond "INVALID_JSON: [error]" and stop
3. Add/replace "statusLine" key:
   {
     "type": "command",
     "command": "${CLAUDE_PLUGIN_ROOT}/scripts/statusline.sh",
     "padding": 0
   }
4. Preserve all other keys, write with 2-space indent
5. Validate result is valid JSON
6. Respond "SUCCESS" with summary
```

## Step 3: Handle Response

- **NOT_FOUND**: Warn user the file doesn't exist. Do NOT create it. Exit.
- **INVALID_JSON**: Show error details. Exit.
- **SUCCESS**: Confirm the statusline configuration was successfully added.
