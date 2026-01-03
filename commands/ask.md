---
description: Ask questions and receive answers without any file modifications
argument-hint: your question(s) [model]
allowed-tools: Task
---

# Ask Questions - Delegated Mode

This command delegates question answering to a general-purpose agent while maintaining read-only restrictions.

## Usage
- `/ask your question here` (uses default Sonnet model)
- `/ask your question here haiku` (uses Haiku model)
- `/ask your question here sonnet` (uses Sonnet model) 
- `/ask your question here opus` (uses Opus model)

## Processing Arguments
Parsing arguments to extract optional model specification:

```
Arguments: $ARGUMENTS
```

Extracting model preference and task:
- If last argument is "haiku", "sonnet", or "opus", use that model
- Otherwise use default: Sonnet (claude-3-5-sonnet-20241022)
- Remaining arguments form the actual question/task

Delegating to general-purpose agent with the following task:

You are delegating a question-answering task to a general-purpose agent. Parse the arguments to determine model preference and extract the actual question.

**Arguments:** $ARGUMENTS

**Instructions for Agent:**

You are in answer-only mode. Your task is to answer the following question(s) without making any modifications to files or code.

**IMPORTANT RULES:**
- DO NOT use any file editing tools (Edit, Write, MultiEdit, NotebookEdit)
- DO NOT create, modify, or delete any files  
- DO NOT run any commands that would modify the file system
- You MAY read files if needed to answer the question
- You MAY search for information in files
- You MAY use web search or fetch to gather information
- Focus solely on providing informative answers

**CODE ANALYSIS TOOLS:**
- When analyzing code structure, architecture, or functionality, prefer using Serena MCP tools if available:
  - `mcp__serena__find_symbol` - Find specific symbols/code entities
  - `mcp__serena__get_symbols_overview` - Get overview of code structure
  - `mcp__serena__search_for_pattern` - Search for code patterns
  - `mcp__serena__find_referencing_symbols` - Find code references
- These tools provide more efficient and structured code analysis than basic file reading

Please provide a clear, comprehensive answer to the question. If you need to reference code or files to answer the question, you may read them, but do not modify anything.