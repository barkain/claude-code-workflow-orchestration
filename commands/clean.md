---
description: Remove unnecessary files from the project with safety checks
argument-hint: [model]
allowed-tools: Task
---

# Clean - Remove Unnecessary Files (Delegated)

This command delegates project cleanup to a general-purpose agent while preserving all safety checks and functionality.

## Usage
- `/clean` (uses default Sonnet model)
- `/clean haiku` (uses Haiku model)
- `/clean sonnet` (uses Sonnet model) 
- `/clean opus` (uses Opus model)

## Task Delegation

**Arguments:** $ARGUMENTS

You are delegating a project cleanup task to a general-purpose agent. Parse arguments for optional model preference (default: Sonnet).

**Instructions for Agent:**

Remove common unnecessary files from the project with safety checks by executing the following commands exactly:

```bash
echo "🧹 Cleaning up project files..."
echo

# Clean Python cache files
echo "🐍 Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
find . -name "*.pyd" -delete 2>/dev/null
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null
find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null
find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null
echo "✅ Python cache cleaned"
echo

# Clean OS-specific files
echo "💻 Removing OS-specific files..."
find . -name ".DS_Store" -delete 2>/dev/null
find . -name "Thumbs.db" -delete 2>/dev/null
find . -name "desktop.ini" -delete 2>/dev/null
echo "✅ OS files cleaned"
echo

# Clean editor files
echo "📝 Removing editor temporary files..."
find . -name "*.swp" -delete 2>/dev/null
find . -name "*.swo" -delete 2>/dev/null
find . -name "*~" -delete 2>/dev/null
find . -name "*.bak" -delete 2>/dev/null
find . -name "*.tmp" -delete 2>/dev/null
echo "✅ Editor files cleaned"
echo

# Clean build artifacts
echo "🔨 Removing build artifacts..."
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null
find . -name "dist" -type d -not -path "./.venv/*" -not -path "./venv/*" -not -path "./node_modules/*" -exec rm -rf {} + 2>/dev/null
find . -name "build" -type d -not -path "./.venv/*" -not -path "./venv/*" -not -path "./node_modules/*" -exec rm -rf {} + 2>/dev/null
find . -name "*.egg" -delete 2>/dev/null
echo "✅ Build artifacts cleaned"
echo

# Show remaining untracked files
echo "📋 Remaining untracked files:"
git_untracked=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l)
if [ "$git_untracked" -gt 0 ]; then
    echo "Found $git_untracked untracked files. To review them:"
    echo "  git status --porcelain | grep '^??'"
    echo "To remove all untracked files (CAREFUL!):"
    echo "  git clean -fd"
else
    echo "No untracked files found"
fi
echo

echo "✨ Cleanup complete!"
```

This command safely removes:
- Python cache files (__pycache__, *.pyc, *.pyo)
- Test/tool caches (.pytest_cache, .ruff_cache, .mypy_cache)
- OS-specific files (.DS_Store, Thumbs.db)
- Editor temporary files (*.swp, *~, *.bak)
- Build artifacts (dist/, build/, *.egg-info)

Files in .venv/, venv/, and node_modules/ are protected from deletion.