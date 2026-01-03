#!/usr/bin/env bash

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║  Claude Workflow Orchestration - Installation Script                           ║
# ╠════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                ║
# ║  This system supports TWO installation methods:                                ║
# ║                                                                                ║
# ║  1. MANUAL INSTALLATION (this script)                                          ║
# ║     - Copies files to /path/to/project/.claude/ or ~/.claude/                  ║
# ║     - Best for: single-project setup, customization, offline use               ║
# ║     - Run: ./install.sh                                                        ║
# ║                                                                                ║
# ║  2. PLUGIN INSTALLATION (recommended for multi-project)                        ║
# ║     - Registers this directory as a Claude Code plugin                         ║
# ║     - Best for: version control, easy updates, project portability             ║
# ║     - Run: /plugin install workflow-orchestration                              ║
# ║                                                                                ║
# ╚════════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# Get the directory where this script is located
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# State tracking for interrupt handling
BACKUP_PATH=""
INSTALLATION_STARTED=false
CLAUDE_DIR=""
INSTALLATION_SCOPE=""

# Argument parsing state
TARGET_DIR="~"
SCOPE=""
SHOW_HELP=false

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Directories and files to copy
readonly DIRS_TO_COPY=("agents" "commands" "hooks" "scripts" "system-prompts" "output-styles")
# Note: settings.json is handled separately by merge_settings_json() for intelligent merging
readonly FILES_TO_COPY=()

# Hooks that need to be made executable
readonly EXECUTABLE_HOOKS=(
    "hooks/PostToolUse/*.sh"
    "hooks/PreToolUse/*.sh"
    "hooks/SessionStart/*.sh"
    "hooks/stop/*.sh"
    "hooks/SubagentStop/*.sh"
    "hooks/UserPromptSubmit/*.sh"
    "scripts/statusline.sh"
)

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_success() { print_message "$GREEN" "✓ $1"; }
print_error() { print_message "$RED" "✗ $1"; }
print_info() { print_message "$BLUE" "ℹ $1"; }
print_warning() { print_message "$YELLOW" "⚠ $1"; }

# Parse command line arguments
# Sets global variables: SCOPE, TARGET_DIR, SHOW_HELP
parse_arguments() {
    SCOPE=""
    TARGET_DIR="~"
    SHOW_HELP=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --scope=*)
                SCOPE="${1#--scope=}"
                shift
                ;;
            --scope)
                if [[ -n "${2:-}" && ! "$2" =~ ^- ]]; then
                    SCOPE="$2"
                    shift 2
                else
                    print_error "--scope requires a value"
                    exit 1
                fi
                ;;
            -h|--help)
                SHOW_HELP=true
                shift
                ;;
            -*)
                print_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
            *)
                TARGET_DIR="$1"
                shift
                ;;
        esac
    done
}

# Detect installation scope based on environment, CLI args, or user prompt
# Priority: 1) CLAUDE_PLUGIN_ROOT env var, 2) CLI --scope arg, 3) Interactive prompt
# Returns: "plugin", "project", or "user"
# Note: All user-facing output goes to stderr; only the scope value goes to stdout
detect_installation_scope() {
    local cli_scope="${1:-}"

    # Priority 1: Check for CLAUDE_PLUGIN_ROOT environment variable
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
        print_info "Detected plugin installation (CLAUDE_PLUGIN_ROOT is set)" >&2
        echo "plugin"
        return 0
    fi

    # Priority 2: Check CLI argument
    if [[ -n "$cli_scope" ]]; then
        case "$cli_scope" in
            plugin|project|user)
                print_info "Using scope from CLI argument: $cli_scope" >&2
                echo "$cli_scope"
                return 0
                ;;
            *)
                print_error "Invalid scope: $cli_scope" >&2
                print_error "Valid scopes: plugin, project, user" >&2
                return 1
                ;;
        esac
    fi

    # Priority 3: Interactive prompt
    echo >&2
    print_info "Select installation scope:" >&2
    echo "  1) user    - Install to ~/.claude/ (applies to all projects)" >&2
    echo "  2) project - Install to ./.claude/ (current project only)" >&2
    echo >&2

    local choice
    while true; do
        read -rp "Enter choice [1-2]: " choice
        case "$choice" in
            1|user)
                echo "user"
                return 0
                ;;
            2|project)
                echo "project"
                return 0
                ;;
            *)
                print_warning "Invalid choice. Please enter 1 or 2." >&2
                ;;
        esac
    done
}

# Cleanup handler for interrupted installations
# Restores from backup if available, otherwise warns about partial installation
cleanup_on_interrupt() {
    echo ""
    print_warning "Installation interrupted!"

    if [[ "$INSTALLATION_STARTED" == "true" && -n "$BACKUP_PATH" && -d "$BACKUP_PATH" ]]; then
        print_info "Restoring from backup: $BACKUP_PATH"
        rm -rf "$CLAUDE_DIR"
        mv "$BACKUP_PATH" "$CLAUDE_DIR"
        print_info "Previous installation restored"
    elif [[ "$INSTALLATION_STARTED" == "true" ]]; then
        print_warning "Partial installation may exist at $CLAUDE_DIR"
        print_warning "Please run install.sh again or manually clean up"
    fi

    exit 130
}

# Set up trap for SIGINT (Ctrl+C) and SIGTERM
trap cleanup_on_interrupt SIGINT SIGTERM

# Backup existing installation before making changes
# Creates a timestamped backup of the .claude directory if it exists
# Sets BACKUP_PATH global variable for use by trap handler in restore operations
backup_existing_installation() {
    local claude_dir=$1

    # If directory does not exist, nothing to backup
    if [[ ! -d "$claude_dir" ]]; then
        print_info "No existing installation found at $claude_dir - skipping backup"
        return 0
    fi

    # Create timestamped backup name
    local backup_name="${claude_dir}.backup.$(date +%Y%m%d_%H%M%S)"

    print_info "Existing installation found at $claude_dir"
    print_info "Creating backup at: $backup_name"

    if cp -r "$claude_dir" "$backup_name"; then
        print_success "Backup created successfully: $backup_name"
        # Set global variable for trap handler restore operations
        BACKUP_PATH="$backup_name"
        return 0
    else
        print_error "Failed to create backup of existing installation"
        print_error "Aborting installation to prevent data loss"
        return 1
    fi
}

# Display installation method banner
print_install_banner() {
    local target_dir=$1
    echo
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}Claude Workflow Orchestration - Installation${NC}                    ${BLUE}║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║${NC}  Method: ${YELLOW}Manual Installation${NC} (install.sh)                        ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  Target: ${GREEN}$target_dir${NC}                                         ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Display completion message with alternative installation info
print_completion_banner() {
    local claude_dir=$1
    local scope=${2:-"unknown"}

    # Format scope display
    local scope_display
    case "$scope" in
        user)     scope_display="User (~/.claude)" ;;
        project)  scope_display="Project (.claude)" ;;
        *)        scope_display="$scope" ;;
    esac

    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${GREEN}Installation Complete!${NC}                                           ${GREEN}║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  Files copied to $claude_dir successfully.                         ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Scope: ${YELLOW}${scope_display}${NC}                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${YELLOW}Alternative: Plugin Installation${NC}                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  For multi-project setups, consider plugin installation:          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}    ${BLUE}/plugin install workflow-orchestration${NC}                        ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Plugin benefits:                                                  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}    - Automatic updates when repo changes                          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}    - Per-project configuration                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}    - No file copying required                                     ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Print usage information
print_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TARGET_DIR]

Claude Workflow Orchestration - Manual Installation

This script copies files from src/ to TARGET_DIR/.claude/.
For plugin-based installation, use: /plugin install workflow-orchestration

Options:
  --scope=SCOPE   Installation scope for path resolution
                    plugin  - Keep \${CLAUDE_PLUGIN_ROOT} (for plugin system)
                    project - Replace with ./.claude (current project only)
                    user    - Replace with ~/.claude (all projects)
                  If not specified, will prompt interactively.

  -h, --help      Show this help message

Arguments:
  TARGET_DIR    Target directory for installation (default: ~)
                System will be installed to TARGET_DIR/.claude/

Examples:
  $0                       # Interactive scope selection
  $0 --scope=user          # Install with user scope (~/.claude paths)
  $0 --scope=project       # Install with project scope (./.claude paths)
  $0 --scope=user /opt     # Install to /opt/.claude with user scope

Installation Methods:
  Manual (this script):
    - Copies files to ~/.claude/
    - Best for: single-project, customization, offline use

  Plugin (/plugin install):
    - Registers repo as Claude Code plugin
    - Best for: multi-project, version control, easy updates

EOF
}

# Validate source directory
validate_source() {
    print_info "Validating source files..."

    local missing_items=()

    # Check directories
    for dir in "${DIRS_TO_COPY[@]}"; do
        if [[ ! -d "$SCRIPT_DIR/$dir" ]]; then
            missing_items+=("directory: $dir")
        fi
    done

    # Check files (from FILES_TO_COPY array)
    # Use safe array expansion pattern to handle empty arrays with set -u
    for file in ${FILES_TO_COPY[@]+"${FILES_TO_COPY[@]}"}; do
        if [[ ! -f "$SCRIPT_DIR/$file" ]]; then
            missing_items+=("file: $file")
        fi
    done

    # Check settings.json separately (handled by merge_settings_json)
    if [[ ! -f "$SCRIPT_DIR/settings.json" ]]; then
        missing_items+=("file: settings.json")
    fi

    if [[ ${#missing_items[@]} -gt 0 ]]; then
        print_error "Missing source files or directories:"
        for item in "${missing_items[@]}"; do
            echo "  - $item"
        done
        return 1
    fi

    print_success "All source files found"
    return 0
}

# Validate target directory
validate_target() {
    local target_dir=$1

    print_info "Validating target directory: $target_dir"

    # Expand tilde
    target_dir="${target_dir/#\~/$HOME}"

    # Check if target directory exists or can be created
    if [[ ! -d "$target_dir" ]]; then
        print_error "Target directory does not exist: $target_dir"
        return 1
    fi

    # Check write permissions
    if [[ ! -w "$target_dir" ]]; then
        print_error "No write permission for target directory: $target_dir"
        return 1
    fi

    print_success "Target directory is valid and writable"
    return 0
}

# Create directory structure
create_directory_structure() {
    local claude_dir=$1

    print_info "Creating directory structure..."

    if [[ ! -d "$claude_dir" ]]; then
        if mkdir -p "$claude_dir"; then
            print_success "Created directory: $claude_dir"
        else
            print_error "Failed to create directory: $claude_dir"
            return 1
        fi
    else
        print_info "Directory already exists: $claude_dir"
    fi

    # Create subdirectories
    for dir in "${DIRS_TO_COPY[@]}"; do
        local target_subdir="$claude_dir/$dir"
        if [[ ! -d "$target_subdir" ]]; then
            if mkdir -p "$target_subdir"; then
                print_success "Created subdirectory: $dir"
            else
                print_error "Failed to create subdirectory: $dir"
                return 1
            fi
        fi
    done

    return 0
}

# Copy files and directories
copy_files() {
    local claude_dir=$1

    print_info "Copying delegation system files..."

    # Copy directories
    for dir in "${DIRS_TO_COPY[@]}"; do
        print_info "Copying $dir/..."
        if cp -r "$SCRIPT_DIR/$dir"/* "$claude_dir/$dir/" 2>/dev/null; then
            print_success "Copied $dir/"
        else
            print_warning "No files found in $dir/ or copy failed"
        fi
    done

    # Copy individual files (if any - settings.json is handled separately by merge_settings_json)
    # Use safe array expansion pattern to handle empty arrays with set -u
    for file in ${FILES_TO_COPY[@]+"${FILES_TO_COPY[@]}"}; do
        print_info "Copying $file..."
        if cp "$SCRIPT_DIR/$file" "$claude_dir/$file"; then
            print_success "Copied $file"
        else
            print_error "Failed to copy $file"
            return 1
        fi
    done

    return 0
}

# Resolve ${CLAUDE_PLUGIN_ROOT} variable references in settings.json based on installation scope
# Handles three scopes:
# - plugin: keeps variable references unchanged (for runtime resolution)
# - project: replaces with ./.claude (relative project path)
# - user: replaces with ~/.claude (user home path)
resolve_settings_json_paths() {
    local scope="$1"
    local source_settings="$2"
    local output_file="$3"

    # Validate inputs
    if [[ ! -f "$source_settings" ]]; then
        print_error "Source settings.json not found: $source_settings"
        return 1
    fi

    case "$scope" in
        plugin)
            # No substitution needed - copy as-is
            print_info "Plugin scope: keeping \${CLAUDE_PLUGIN_ROOT} variable references"
            cp "$source_settings" "$output_file"
            return $?
            ;;

        project)
            # Replace with relative project path
            local replacement="./.claude"
            print_info "Project scope: replacing \${CLAUDE_PLUGIN_ROOT} with $replacement"
            sed 's|\${CLAUDE_PLUGIN_ROOT}|'"$replacement"'|g' "$source_settings" > "$output_file"
            return $?
            ;;

        user)
            # Replace with user home path (literal tilde for portability)
            local replacement="~/.claude"
            print_info "User scope: replacing \${CLAUDE_PLUGIN_ROOT} with $replacement"
            sed 's|\${CLAUDE_PLUGIN_ROOT}|'"$replacement"'|g' "$source_settings" > "$output_file"
            return $?
            ;;

        *)
            print_error "Invalid scope: $scope"
            return 1
            ;;
    esac
}

# Merge settings.json intelligently, preserving user customizations
# Handles three cases:
# 1. No existing settings.json - simple copy (with path resolution)
# 2. Existing file + jq available - smart merge preserving user settings
# 3. Existing file + no jq - backup and copy with warning
merge_settings_json() {
    local claude_dir=$1
    local scope=${2:-"user"}
    local src_settings="$SCRIPT_DIR/settings.json"
    local dest_settings="$claude_dir/settings.json"

    print_info "Processing settings.json (scope: $scope)..."

    # Validate source file exists
    if [[ ! -f "$src_settings" ]]; then
        print_error "Source settings.json not found: $src_settings"
        return 1
    fi

    # Create temp file with resolved paths for the given scope
    local temp_resolved
    temp_resolved=$(mktemp)

    if ! resolve_settings_json_paths "$scope" "$src_settings" "$temp_resolved"; then
        print_error "Failed to resolve paths in settings.json"
        rm -f "$temp_resolved"
        return 1
    fi

    # Case 1: No existing settings.json - simple copy (using resolved paths)
    if [[ ! -f "$dest_settings" ]]; then
        print_info "Installing new settings.json (no existing file found)"
        if cp "$temp_resolved" "$dest_settings"; then
            print_success "Installed settings.json with $scope scope paths"
            rm -f "$temp_resolved"
            return 0
        else
            print_error "Failed to copy settings.json"
            rm -f "$temp_resolved"
            return 1
        fi
    fi

    # Existing file found - need to merge or backup
    print_info "Existing settings.json found at $dest_settings"

    # Case 2: Existing file + jq available - smart merge
    if command -v jq &>/dev/null; then
        print_info "Merging settings.json (preserving user customizations)"

        # Create temp file for merged result
        local temp_merged
        temp_merged=$(mktemp)

        # Deep merge using jq:
        # - User's settings take precedence for scalar values
        # - For hooks arrays, we append new hooks from plugin
        # - New top-level keys from plugin are added
        # Note: Using temp_resolved (scope-adjusted paths) instead of src_settings
        if jq -s '
            # Helper function to merge hook arrays
            def merge_hook_arrays($a; $b):
                ($a // []) + (($b // []) | map(select(
                    . as $new | ($a // []) | all(. != $new)
                )));

            # Merge hooks object - append new hooks to each hook type
            def merge_hooks($user; $plugin):
                ($user // {}) as $u |
                ($plugin // {}) as $p |
                ($u | keys) + ($p | keys) | unique |
                reduce .[] as $key ({};
                    . + {($key): merge_hook_arrays($u[$key]; $p[$key])}
                );

            # Main merge: user settings (.[0]) take precedence
            # Plugin settings (.[1]) provide defaults and new hooks
            .[0] as $user | .[1] as $plugin |
            $plugin * $user * {
                "hooks": merge_hooks($user.hooks; $plugin.hooks),
                "permissions": {
                    "allow": (($user.permissions.allow // []) + ($plugin.permissions.allow // []) | unique),
                    "deny": (($user.permissions.deny // []) + ($plugin.permissions.deny // []) | unique)
                }
            }
        ' "$dest_settings" "$temp_resolved" > "$temp_merged" 2>/dev/null; then
            # Validate the merged JSON
            if jq empty "$temp_merged" 2>/dev/null; then
                if cp "$temp_merged" "$dest_settings"; then
                    print_success "Merged settings.json (user customizations preserved, $scope scope paths)"
                    rm -f "$temp_merged" "$temp_resolved"
                    return 0
                else
                    print_error "Failed to write merged settings.json"
                    rm -f "$temp_merged" "$temp_resolved"
                    return 1
                fi
            else
                print_warning "Merged settings.json is invalid, falling back to backup method"
                rm -f "$temp_merged"
            fi
        else
            print_warning "jq merge failed, falling back to backup method"
            rm -f "$temp_merged"
        fi
    fi

    # Case 3: Existing file + no jq (or jq merge failed) - backup and copy with warning
    local backup_name="${dest_settings}.backup.$(date +%Y%m%d_%H%M%S)"
    print_warning "jq not available or merge failed - backing up existing settings"

    if cp "$dest_settings" "$backup_name"; then
        print_info "Backed up existing settings to: $backup_name"
        if cp "$temp_resolved" "$dest_settings"; then
            print_success "Installed new settings.json with $scope scope paths"
            print_warning "WARNING: Your existing settings.json was backed up to:"
            print_warning "  $backup_name"
            print_warning "Please manually merge any customizations you had."
            rm -f "$temp_resolved"
            return 0
        else
            print_error "Failed to copy new settings.json"
            # Restore backup
            cp "$backup_name" "$dest_settings"
            rm -f "$temp_resolved"
            return 1
        fi
    else
        print_error "Failed to backup existing settings.json"
        rm -f "$temp_resolved"
        return 1
    fi
}

# Make hooks executable after installation
# Iterates through EXECUTABLE_HOOKS array, expands glob patterns,
# applies chmod +x to each hook, and logs operations
make_hooks_executable() {
    local claude_dir=$1

    print_info "Making hooks executable..."

    local made_executable=0
    local not_found=0

    for hook_pattern in "${EXECUTABLE_HOOKS[@]}"; do
        # Expand glob pattern relative to claude_dir
        local hook_path="$claude_dir/$hook_pattern"

        # Use glob expansion to handle wildcards
        # shellcheck disable=SC2086
        for hook_file in $hook_path; do
            if [[ -f "$hook_file" ]]; then
                if chmod +x "$hook_file"; then
                    print_success "chmod +x $(basename "$hook_file")"
                    ((made_executable++))
                else
                    print_warning "Failed to chmod +x: $hook_file"
                fi
            elif [[ "$hook_file" == *'*'* ]]; then
                # Pattern didn't expand (no matches found)
                print_warning "No files matched pattern: $hook_pattern"
                ((not_found++))
            else
                print_warning "Hook not found: $hook_file"
                ((not_found++))
            fi
        done
    done

    if [[ $made_executable -gt 0 ]]; then
        print_success "Made $made_executable hooks executable"
    fi

    if [[ $not_found -gt 0 ]]; then
        print_warning "$not_found hook patterns had no matches"
    fi

    return 0
}

# Main installation function
main() {
    # Parse arguments
    parse_arguments "$@"

    # Show help if requested
    if [[ "$SHOW_HELP" == "true" ]]; then
        print_usage
        exit 0
    fi

    # Expand tilde in target_dir
    local target_dir="${TARGET_DIR/#\~/$HOME}"
    local claude_dir="$target_dir/.claude"

    # Set global CLAUDE_DIR for trap handler
    CLAUDE_DIR="$claude_dir"

    # Display installation method banner
    print_install_banner "$claude_dir"

    # Validate source files
    if ! validate_source; then
        print_error "Installation aborted: Source validation failed"
        exit 1
    fi
    echo

    # Validate target directory
    if ! validate_target "$target_dir"; then
        print_error "Installation aborted: Target validation failed"
        exit 1
    fi
    echo

    # Detect installation scope
    local installation_scope
    installation_scope=$(detect_installation_scope "$SCOPE")
    if [[ $? -ne 0 ]]; then
        print_error "Installation aborted: Invalid scope"
        exit 1
    fi
    INSTALLATION_SCOPE="$installation_scope"

    # Update target directory based on detected scope
    # This must happen AFTER scope detection to use the correct directory
    case "$installation_scope" in
        user)
            target_dir="$HOME"
            ;;
        project)
            target_dir="$(pwd)"
            ;;
        plugin)
            # Keep the original target_dir for plugin installation
            # (typically set via CLAUDE_PLUGIN_ROOT or command line)
            ;;
    esac
    claude_dir="$target_dir/.claude"
    CLAUDE_DIR="$claude_dir"
    print_info "Installation target: $claude_dir (scope: $installation_scope)"
    echo

    # Backup existing installation before making any changes
    if ! backup_existing_installation "$claude_dir"; then
        print_error "Installation aborted: Backup failed"
        exit 1
    fi
    echo

    # Create directory structure
    if ! create_directory_structure "$claude_dir"; then
        print_error "Installation aborted: Failed to create directory structure"
        exit 1
    fi
    echo

    # Mark installation as started for trap handler
    INSTALLATION_STARTED=true

    # Merge settings.json intelligently (preserves user customizations)
    if ! merge_settings_json "$claude_dir" "$installation_scope"; then
        print_error "Installation aborted: Failed to process settings.json"
        exit 1
    fi
    echo

    # Copy files
    if ! copy_files "$claude_dir"; then
        print_error "Installation aborted: Failed to copy files"
        exit 1
    fi
    echo

    # Make hooks executable
    if ! make_hooks_executable "$claude_dir"; then
        print_error "Installation aborted: Failed to make hooks executable"
        exit 1
    fi
    echo

    # Print success summary with dual-mode info
    print_completion_banner "$claude_dir" "$installation_scope"

    print_info "Installation location: $claude_dir"
    if [[ -n "$BACKUP_PATH" ]]; then
        print_info "Previous installation backed up to: $BACKUP_PATH"
    fi
    echo
    print_info "Next steps:"
    echo "  1. Verify installation: ls -la $claude_dir"
    echo "  2. Test delegation: claude '/delegate test task'"
    echo "  3. Read documentation: cat $claude_dir/../CLAUDE.md"
    echo
    print_info "For debug mode, run:"
    echo "  export DEBUG_DELEGATION_HOOK=1"
    echo "  tail -f /tmp/delegation_hook_debug.log"
    echo

    exit 0
}

# Run main function
main "$@"
