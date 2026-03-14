# MANDATORY: Token-Efficient CLI Usage Rules

These rules are REQUIRED for all CLI command usage. Violations waste context tokens and degrade session quality.

**ALWAYS use the compact form. NEVER use the verbose form.**

You MUST follow every rule below. These are not suggestions — they are binding constraints on your behavior. When you run a Bash command, you MUST use the minimal-output form listed here. The verbose forms are PROHIBITED.

---

## Git

| REQUIRED (use this) | PROHIBITED (never use this) |
|---|---|
| `git status -sb` | `git status` |
| `git log --oneline -n 10` | `git log` |
| `git diff --stat` (overview first) | `git diff` (full diff without scoping) |
| `git branch --format='%(refname:short)'` | `git branch`, `git branch -a`, `git branch -v` |
| `git show --stat <ref>` (before full content) | `git show <ref>` (unbounded) |
| `git commit --quiet` | `git commit` (verbose) |
| `git push --quiet` | `git push` (verbose) |
| `git pull --quiet` | `git pull` (verbose) |
| `git fetch --quiet` | `git fetch` (verbose) |
| `git merge --quiet` | `git merge` (verbose) |
| `git rebase --quiet` | `git rebase` (verbose) |
| `git stash --quiet` | `git stash` (verbose) |

- `git add --verbose` is unnecessary — MUST use `git add <paths>` without flags.
- For full diff: MUST scope to specific files (`git diff -- path/to/file`), never dump the entire diff.

## Search (rg / grep)

- MUST use `rg --no-heading --count <pattern>` for initial scan, then targeted search on specific files.
- MUST use `rg -m 5 <pattern>` to cap matches per file.
- MUST scope searches to relevant directories. NEVER search from repo root without filters.
- MUST use `rg -l <pattern>` (files-only) when you just need to know *where*.
- MUST use `rg --max-columns 120 --max-columns-preview <pattern>` to truncate long match lines.
- MUST use `rg -g '*.py' <pattern>` to limit by filetype instead of searching everything.

## File Inspection

| REQUIRED (use this) | PROHIBITED (never use this) |
|---|---|
| `ls -1` | `ls -la`, `ls -l`, `ls -al` (when permissions/sizes are irrelevant) |
| `head -50 <file>` or `sed -n '10,30p' <file>` | `cat <file>` on files over 50 lines |
| `tree -L 2 --dirsfirst -I '...'` | `tree` (unbounded) |
| `find . -type f -name '*.py' \| head -30` | Recursive `ls` |

- MUST run `wc -l <file>` before reading to gauge size.
- For a quick file summary: `wc -l <file> && grep -cE '^\s*(def |class |fn |function |export )' <file>`.
- For Python signature overview: `grep -n 'def \|class ' <file>` instead of reading the full file.
- For JS/TS signature overview: `grep -n 'function \|export \|interface \|class ' <file>`.

## JSON Inspection

- MUST see structure before values: `jq 'keys' <file>` or `jq 'walk(if type == "string" then "str" elif type == "number" then "num" elif type == "boolean" then "bool" else . end)' <file>`.
- For arrays: `jq '{length: length, first: .[0]}' <file>`.
- When curling JSON APIs: `curl -sS <url> | jq 'keys'` to inspect shape first.

## Environment Variables

- NEVER run bare `env` or `printenv`.
- MUST filter: `env | grep ^AWS` or `env | grep -iE '^(AWS|DATABASE|REDIS|API)' | sort`.

## Python

| REQUIRED (use this) | PROHIBITED (never use this) |
|---|---|
| `pytest -q --tb=short --no-header` | `pytest` (default verbose output) |
| `ruff check --output-format concise --quiet` | `ruff check` (bare, without `--output-format concise --quiet`) |
| `mypy --no-error-summary --hide-error-context` | `mypy` (verbose) |
| `pip install -q` / `uv pip install --quiet` | `pip install` / `uv pip install` (verbose) |

**Ruff rule (MANDATORY):** ALWAYS run `ruff check --output-format concise --quiet`. NEVER run bare `ruff check` without `--output-format concise --quiet`.

## JavaScript / TypeScript

- MUST use `npm test -- --silent` or `npx vitest run --reporter=dot`.
- MUST use `npx tsc --pretty false --noEmit 2>&1` for type checking.
- MUST use `npx eslint --format compact`.
- MUST use `pnpm ls --depth 0` instead of full dependency tree.

## Rust

- MUST use `cargo test --quiet 2>&1` / `cargo build --quiet`.
- MUST use `cargo clippy --quiet --message-format short`.

## Docker

| REQUIRED (use this) | PROHIBITED (never use this) |
|---|---|
| `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'` | `docker ps` (default verbose) |
| `docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'` | `docker images` (default verbose) |
| `docker logs --tail 50 <container>` | `docker logs <container>` (unbounded) |

## Kubernetes

- MUST use `kubectl get pods -o wide` or custom-columns format.
- MUST use `kubectl logs --tail=50 <pod>`. NEVER unbounded logs.

## GitHub CLI

- MUST use `--json` + `--jq` for structured output:
  - `gh pr list --json number,title,state --jq '.[] | "\(.number) \(.title) [\(.state)]"'`
  - `gh issue list --json number,title,labels --jq '.[] | "\(.number) \(.title)"'`
  - `gh run list --json name,status,conclusion --jq '.[] | "\(.name) \(.status) \(.conclusion)"'`

## Network

- MUST use `curl -sS` (silent + show errors) always. NEVER bare `curl`.
- MUST use `wget -q` always. NEVER bare `wget`.

## Dependencies

- MUST cap output: `pip list --format=columns | head -30` or `uv pip list | head -30`.
- MUST use `pnpm ls --depth 0` / `npm ls --depth 0`. NEVER full dependency tree.
- MUST use `cargo tree --depth 1`. NEVER full tree.
- MUST use `go list -m all | wc -l` to count before listing.

## General Rules (apply to ALL commands)

1. MUST pipe through `| head -N` or `| tail -N` when output may exceed 50 lines.
2. When only success/failure matters: `<cmd> > /dev/null 2>&1 && echo "ok" || echo "FAILED: $?"`.
3. MUST NOT run a command a second time just to re-read its output — capture to variable if needed.
4. MUST use `--no-pager` on commands that might invoke a pager (git, man, etc.).
5. MUST NOT use `--verbose`, `-v`, `-la`, or any flag that increases output unless the extra detail is specifically needed for the current task.
