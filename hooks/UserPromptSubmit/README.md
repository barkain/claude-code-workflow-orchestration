# UserPromptSubmit Hooks

## Purpose
UserPromptSubmit hooks manage and orchestrate user prompt interactions, providing:
- Prompt preprocessing
- Contextual enhancement
- Interaction tracking

## Current Implementation
`orchestration-reminder.py`: A script designed to manage and enhance user prompt submissions.

## Key Objectives
- Preprocess and validate user prompts
- Inject contextual information
- Apply interaction guidelines
- Prepare prompts for further processing

## Workflow Diagram

```mermaid
flowchart TD
    A["User Submits Prompt"] --> B{"ORCHESTRATION_MODE?"}

    B --> |"active"| C["Generate Orchestration Status"]
    B --> |"not active"| D["Standard Prompt Processing"]

    C --> E["Check Session Variables"]
    E --> F["SESSION_ID: {session_id}"]
    E --> G["DELEGATION_COUNT: {count}"]
    E --> H["LAST_BLOCKED_TOOL: {tool}"]
    E --> I["NEEDS_DISTILLATION: {status}"]

    F --> J["Build Status Message"]
    G --> J
    H --> J
    I --> J

    J --> K["Generate System Reminder"]
    K --> L["🎯 ORCHESTRATION MODE ACTIVE"]
    K --> M["Remember: Delegate via Task tool"]
    K --> N["Maintain high-level context only"]

    D --> O["Proceed to Claude Processing"]
    L --> P["Attach Reminder to Context"]
    M --> P
    N --> P
    P --> O
```

## Workflow
1. Receive initial user prompt
2. Apply preprocessing rules
3. Enhance prompt with contextual metadata
4. Prepare for system interaction

## Implementation Details
- Analyze prompt structure and content
- Apply contextual reminder mechanisms
- Potentially modify or augment prompt

## Logging
Implement comprehensive logging to track:
- Prompt origin
- Preprocessing steps
- Contextual enhancements
- Interaction metadata

## Example Use Cases
- Apply system-wide interaction guidelines
- Inject contextual reminders
- Validate prompt against usage policies
- Prepare prompts for specialized routing

## Current Status
Experimental implementation under active development.

## Future Enhancements
- More sophisticated prompt preprocessing
- Advanced contextual injection
- Machine learning-based prompt analysis