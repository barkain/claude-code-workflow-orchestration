#!/usr/bin/env python3
"""
Reminds about orchestration mode when active
Sets flag for PreToolUse to enforce delegation on next tool
"""

import json
import os
import sys
from pathlib import Path

STATE_FILE = Path.home() / '.claude' / '.orchestration-state'
SESSION_FILE = Path.home() / '.claude' / '.orchestration-session.json'


def main():
    try:
        # Only activate if orchestration mode is on
        if os.environ.get('ORCHESTRATION_MODE') != 'active':
            sys.exit(0)

        # Write state file for PreToolUse - next tool must be delegated
        STATE_FILE.write_text('true')

        # Load session data from file if exists
        session_data = {}
        if SESSION_FILE.exists():
            try:
                session_data = json.loads(SESSION_FILE.read_text())
            except (json.JSONDecodeError, ValueError):
                session_data = {}

        session_id = session_data.get('session_id', 'not_initialized')
        delegation_count = session_data.get('delegation_count', 0)
        last_blocked = session_data.get('last_blocked_tool', 'none')

        # Build status message
        status_parts = [
            '🎯 ORCHESTRATION MODE ACTIVE',
            'Session: %s' % session_id,
            'Delegations: %s' % delegation_count,
        ]

        if last_blocked != 'none':
            status_parts.append('Last blocked tool: %s' % last_blocked)

        # Output reminder
        reminder_text = (
            '<system-reminder>\n🎯 ORCHESTRATION MODE: Delegate all work via Task tool. '
            'Never use Read/Write/Edit/Bash/Grep/Glob directly. | %s\n</system-reminder>\n' % ' | '.join(status_parts)
        )
        sys.stdout.write(reminder_text)
        sys.stdout.flush()

    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
