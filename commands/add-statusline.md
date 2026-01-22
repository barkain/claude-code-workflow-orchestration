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

Spawn a **general-purpose** subagent with the Task tool:

```
Task(
  subagent_type: "general-purpose",
  description: "Add statusline to settings",
  prompt: "Add statusline configuration to [FILE_PATH].

Use the Read tool to check if file exists. Then:

IF FILE EXISTS:
1. Parse existing JSON
2. Add/merge statusLine key
3. Use Edit tool to update

IF FILE DOES NOT EXIST:
1. Create parent directory if needed: mkdir -p [PARENT_DIR]
2. Use Write tool to create file with this content:
{
  \"statusLine\": {
    \"type\": \"command\",
    \"command\": \"uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/statusline.py\",
    \"padding\": 0
  }
}
3. Report CREATED

statusLine value to add:
{
  \"type\": \"command\",
  \"command\": \"uv run --no-project --script ${CLAUDE_PLUGIN_ROOT}/scripts/statusline.py\",
  \"padding\": 0
}

Respond SUCCESS (updated) or CREATED (new file)."
)
```

## Step 3: Handle Response

- **CREATED**: Inform user the settings file was created and statusline was added.
- **INVALID_JSON**: Show error details. Exit.
- **SUCCESS**: Confirm the statusline configuration was successfully added.
