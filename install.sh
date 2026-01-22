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
readonly DIRS_TO_COPY=("agents" "commands" "hooks" "scripts" "system-prompts" "output-styles" "skills")
# Note: settings.json is processed separately - template merged with hooks from hooks.json
readonly FILES_TO_COPY=()

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

    # Check files required for generating settings.json
    if [[ ! -f "$SCRIPT_DIR/hooks/plugin-hooks.json" ]]; then
        missing_items+=("file: hooks/plugin-hooks.json")
    fi
    if [[ ! -f "$SCRIPT_DIR/settings.json" ]]; then
        missing_items+=("file: settings.json (template)")
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

# Generate settings.json by merging template with hooks from hooks.json
# Sources:
#   - settings.json: Template with permissions, statusLine, alwaysThinkingEnabled
#   - hooks/plugin-hooks.json: Hook configuration (source of truth for hooks)
#   - output-styles/: Output style name (extracted from frontmatter)
# Handles path resolution based on scope:
#   - plugin: keeps ${CLAUDE_PLUGIN_ROOT} variable references
#   - project: replaces with ./.claude
#   - user: replaces with ~/.claude
generate_settings_json() {
    local claude_dir=$1
    local scope=${2:-"user"}
    local settings_template="$SCRIPT_DIR/settings.json"
    local hooks_json="$SCRIPT_DIR/hooks/plugin-hooks.json"
    local dest_settings="$claude_dir/settings.json"

    print_info "Generating settings.json (scope: $scope)..."

    # Validate source files exist
    if [[ ! -f "$settings_template" ]]; then
        print_error "Settings template not found: $settings_template"
        return 1
    fi

    if [[ ! -f "$hooks_json" ]]; then
        print_error "Hooks configuration not found: $hooks_json"
        return 1
    fi

    # Check for jq (required for JSON manipulation)
    if ! command -v jq &>/dev/null; then
        print_error "jq is required to generate settings.json"
        print_error "Please install jq: brew install jq (macOS) or apt install jq (Linux)"
        return 1
    fi

    # Determine path prefix based on scope
    local path_prefix
    case "$scope" in
        plugin)  path_prefix='${CLAUDE_PLUGIN_ROOT}' ;;
        project) path_prefix='./.claude' ;;
        user)    path_prefix='~/.claude' ;;
        *)
            print_error "Invalid scope: $scope"
            return 1
            ;;
    esac

    print_info "Using path prefix: $path_prefix"

    # Read and transform settings template (resolve paths)
    local settings_content
    if [[ "$scope" != "plugin" ]]; then
        settings_content=$(sed "s|\\\${CLAUDE_PLUGIN_ROOT}|$path_prefix|g" "$settings_template")
    else
        settings_content=$(cat "$settings_template")
    fi

    # Read and transform hooks (resolve paths)
    local hooks_content
    if [[ "$scope" != "plugin" ]]; then
        hooks_content=$(sed "s|\\\${CLAUDE_PLUGIN_ROOT}|$path_prefix|g" "$hooks_json")
    else
        hooks_content=$(cat "$hooks_json")
    fi

    # Extract hooks object
    local hooks_object
    hooks_object=$(echo "$hooks_content" | jq '.hooks')

    # Detect output style name from output-styles directory
    local output_style_name=""
    local output_styles_dir="$SCRIPT_DIR/output-styles"
    if [[ -d "$output_styles_dir" ]]; then
        local first_style
        first_style=$(find "$output_styles_dir" -name "*.md" -type f | head -1)
        if [[ -n "$first_style" && -f "$first_style" ]]; then
            local extracted_name
            extracted_name=$(sed -n '/^---$/,/^---$/p' "$first_style" | grep '^name:' | sed 's/^name:[[:space:]]*//')
            if [[ -n "$extracted_name" ]]; then
                output_style_name="$extracted_name"
                print_info "Detected output style: $output_style_name"
            fi
        fi
    fi

    # Build complete settings.json by merging template with hooks
    local temp_settings
    temp_settings=$(mktemp)

    if [[ -n "$output_style_name" ]]; then
        # Add hooks and outputStyle to template
        echo "$settings_content" | jq \
            --argjson hooks "$hooks_object" \
            --arg output_style "$output_style_name" \
            '. + {hooks: $hooks, outputStyle: $output_style}' > "$temp_settings"
    else
        # Add hooks only (no outputStyle)
        echo "$settings_content" | jq \
            --argjson hooks "$hooks_object" \
            '. + {hooks: $hooks}' > "$temp_settings"
    fi

    # Validate generated JSON
    if ! jq empty "$temp_settings" 2>/dev/null; then
        print_error "Generated settings.json is invalid"
        rm -f "$temp_settings"
        return 1
    fi

    # Handle existing settings.json at destination
    if [[ -f "$dest_settings" ]]; then
        print_info "Existing settings.json found - merging..."

        local temp_merged
        temp_merged=$(mktemp)

        # Merge: preserve user settings, REPLACE hooks entirely from source
        if jq -s '
            # Main merge: user (.[0]) settings preserved, new settings (.[1]) provide hooks
            .[0] as $user | .[1] as $new |
            # Start with new settings as base, overlay user settings, then force hooks from source
            $new * $user * {
                "hooks": $new.hooks,  # Replace hooks entirely from source (hooks.json)
                "permissions": {
                    "allow": (($user.permissions.allow // []) + ($new.permissions.allow // []) | unique),
                    "deny": (($user.permissions.deny // []) + ($new.permissions.deny // []) | unique)
                }
            }
        ' "$dest_settings" "$temp_settings" > "$temp_merged" 2>/dev/null; then
            if jq empty "$temp_merged" 2>/dev/null; then
                mv "$temp_merged" "$dest_settings"
                print_success "Merged settings.json (user customizations preserved)"
                rm -f "$temp_settings"
                return 0
            fi
        fi

        # Merge failed - backup and replace
        local backup_name="${dest_settings}.backup.$(date +%Y%m%d_%H%M%S)"
        print_warning "Merge failed - backing up existing settings to: $backup_name"
        cp "$dest_settings" "$backup_name"
        rm -f "$temp_merged"
    fi

    # Install new settings.json
    if mv "$temp_settings" "$dest_settings"; then
        print_success "Generated settings.json with $scope scope"
        return 0
    else
        print_error "Failed to install settings.json"
        rm -f "$temp_settings"
        return 1
    fi
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

    # Generate settings.json from hooks.json (preserves user customizations if merging)
    if ! generate_settings_json "$claude_dir" "$installation_scope"; then
        print_error "Installation aborted: Failed to generate settings.json"
        exit 1
    fi
    echo

    # Copy files
    if ! copy_files "$claude_dir"; then
        print_error "Installation aborted: Failed to copy files"
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
