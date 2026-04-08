# Token-Efficient CLI Usage

Minimize command output and file reads. Verbose output wastes context.

## Principle

Default to the most compact form of every command and file read. Bash commands you run for git, tests, builds, and logs are auto-compressed by a PreToolUse hook (`compact_run.py`) — you don't need to memorize every flag. Focus on the things hooks can't fix: how you *read files* and *scope searches*.

## File reads (Read tool)

- Files >200 lines: use `offset` + `limit` (read ~50 lines around the relevant section).
- Find first, then read: `Grep` for the symbol/heading → note line number → `Read` with `offset`.
- Never read CLAUDE.md, settings.json, or other large config files in full.

## Search (Grep / rg)

- Scope by directory or filetype (`-g '*.py'`), not the whole repo.
- Use `files_with_matches` mode when you only need *where*, not *what*.
- Cap matches with `head_limit` or `-m 5`.

## Bash inspection

- `wc -l <file>` before reading anything unknown.
- `head -50` / `sed -n '10,30p'` instead of `cat` for large files.
- `ls -1` instead of `ls -la` unless you need permissions.
- `rg -l 'def |class '` for signature overviews instead of reading full source.

## General rules

1. Pipe `| head -N` whenever output could exceed ~50 lines.
2. `--no-pager` on git/man and any tool that might invoke a pager.
3. No `&&` chaining except `cd <dir> && <cmd>`. Use separate Bash calls.
4. Don't re-run a command to re-read its output; capture to a variable.
5. When only success/failure matters: `<cmd> >/dev/null 2>&1 && echo ok || echo FAIL`.
6. Filter `env` output: `env | grep ^PREFIX`, never bare `env`.

The PreToolUse hook handles compact flags for: git (status/log/diff/push/pull/commit/etc.), pytest, cargo test, npm/pnpm/yarn/bun test, vitest/jest/mocha/playwright, go test, make test, docker/kubectl logs, eslint, next, tsc. You can run these commands normally — the hook adds the flags.
