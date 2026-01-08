#!/bin/bash
# Wolfies Executive Function Skill Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/wolfiesch/wolfies-executive-function/master/scripts/marketplace/install-skill.sh | bash -s -- <skill-name>
#
# Available skills:
#   wolfies-imessage   - iMessage CLI with semantic search (19x faster than MCP)
#   wolfies-gmail      - Gmail MCP server for Claude Code
#   wolfies-calendar   - Google Calendar MCP server for Claude Code
#   wolfies-reminders  - Apple Reminders MCP server for Claude Code
#   all                - Install all skills

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_RAW_URL="https://raw.githubusercontent.com/wolfiesch/wolfies-executive-function/master"
SKILLS_DIR="${HOME}/.claude/skills"
HOMEBREW_TAP="wolfiesch/executive-function"

# Functions
log_info() { echo -e "${BLUE}==>${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

check_dependencies() {
    if ! command -v brew &>/dev/null; then
        log_error "Homebrew is required but not installed."
        echo "Install it from: https://brew.sh"
        exit 1
    fi

    if ! command -v claude &>/dev/null; then
        log_warn "Claude Code CLI not found. Skills will be installed but may not work until Claude Code is installed."
    fi
}

ensure_tap() {
    if ! brew tap | grep -q "$HOMEBREW_TAP"; then
        log_info "Adding Homebrew tap: $HOMEBREW_TAP"
        brew tap "$HOMEBREW_TAP"
    fi
}

install_formula() {
    local formula=$1
    local formula_name="${formula##*/}"

    if brew list "$formula" &>/dev/null; then
        log_success "$formula_name already installed"
    else
        log_info "Installing $formula_name via Homebrew..."
        brew install "$formula"
        log_success "$formula_name installed"
    fi
}

install_skill_files() {
    local skill_name=$1
    local skill_source=$2

    if [ "$skill_source" = "null" ] || [ -z "$skill_source" ]; then
        log_info "No skill files to install for $skill_name (MCP-only)"
        return 0
    fi

    local target_dir="${SKILLS_DIR}/${skill_name}"
    mkdir -p "$target_dir"

    log_info "Downloading skill files for $skill_name..."

    # Download SKILL.md
    if curl -fsSL "${REPO_RAW_URL}/${skill_source}/SKILL.md" -o "${target_dir}/SKILL.md" 2>/dev/null; then
        log_success "Downloaded SKILL.md"
    else
        log_warn "SKILL.md not found, checking for README.md..."
        if curl -fsSL "${REPO_RAW_URL}/${skill_source}/README.md" -o "${target_dir}/README.md" 2>/dev/null; then
            log_success "Downloaded README.md"
        else
            log_warn "No skill documentation found"
        fi
    fi
}

show_post_install() {
    local skill_name=$1

    echo ""
    log_info "Post-installation steps for $skill_name:"
    echo ""

    case "$skill_name" in
        wolfies-imessage)
            echo "  1. Start the daemon:"
            echo "     brew services start wolfies-imessage"
            echo ""
            echo "  2. Grant Full Disk Access to python3.11:"
            echo "     System Settings > Privacy & Security > Full Disk Access"
            echo ""
            echo "  3. Test it works:"
            echo "     wolfies-imessage health"
            ;;
        wolfies-gmail)
            echo "  1. Create Google OAuth credentials:"
            echo "     https://console.cloud.google.com/apis/credentials"
            echo ""
            echo "  2. Save credentials.json to:"
            echo "     ~/.config/wolfies-gmail/credentials.json"
            echo ""
            echo "  3. Install Python dependencies:"
            echo "     pip3.11 install google-api-python-client google-auth-httplib2 google-auth-oauthlib mcp"
            echo ""
            echo "  4. Register with Claude Code:"
            echo "     claude mcp add -t stdio gmail -- wolfies-gmail-mcp"
            ;;
        wolfies-calendar)
            echo "  1. Create Google OAuth credentials:"
            echo "     https://console.cloud.google.com/apis/credentials"
            echo ""
            echo "  2. Save credentials.json to:"
            echo "     ~/.config/wolfies-calendar/credentials.json"
            echo ""
            echo "  3. Install Python dependencies:"
            echo "     pip3.11 install google-api-python-client google-auth-httplib2 google-auth-oauthlib mcp python-dateutil"
            echo ""
            echo "  4. Register with Claude Code:"
            echo "     claude mcp add -t stdio google-calendar -- wolfies-calendar-mcp"
            ;;
        wolfies-reminders)
            echo "  1. Grant Reminders access:"
            echo "     System Settings > Privacy & Security > Reminders > Enable Terminal"
            echo ""
            echo "  2. Grant Automation access:"
            echo "     System Settings > Privacy & Security > Automation > Terminal > Reminders"
            echo ""
            echo "  3. Install Python dependencies:"
            echo "     pip3.11 install mcp pyobjc-framework-EventKit pyobjc-core"
            echo ""
            echo "  4. Register with Claude Code:"
            echo "     claude mcp add -t stdio reminders -- wolfies-reminders-mcp"
            ;;
    esac
    echo ""
}

install_skill() {
    local skill_name=$1

    log_info "Installing $skill_name..."
    echo ""

    case "$skill_name" in
        wolfies-imessage)
            install_formula "wolfiesch/executive-function/wolfies-imessage"
            install_skill_files "wolfies-imessage" "Texting/skills/imessage-gateway"
            show_post_install "wolfies-imessage"
            ;;
        wolfies-gmail)
            install_formula "wolfiesch/executive-function/wolfies-gmail"
            # Gmail has no skill files currently (MCP-only)
            show_post_install "wolfies-gmail"
            ;;
        wolfies-calendar)
            install_formula "wolfiesch/executive-function/wolfies-calendar"
            install_skill_files "wolfies-calendar" ".claude/skills/managing-google-calendar"
            show_post_install "wolfies-calendar"
            ;;
        wolfies-reminders)
            install_formula "wolfiesch/executive-function/wolfies-reminders"
            # Reminders uses task-capture skill which is separate
            show_post_install "wolfies-reminders"
            ;;
        all)
            for s in wolfies-imessage wolfies-gmail wolfies-calendar wolfies-reminders; do
                install_skill "$s"
                echo "---"
            done
            ;;
        *)
            log_error "Unknown skill: $skill_name"
            echo ""
            echo "Available skills:"
            echo "  wolfies-imessage   - iMessage CLI with semantic search"
            echo "  wolfies-gmail      - Gmail MCP server"
            echo "  wolfies-calendar   - Google Calendar MCP server"
            echo "  wolfies-reminders  - Apple Reminders MCP server"
            echo "  all                - Install all skills"
            exit 1
            ;;
    esac
}

# Main
main() {
    if [ $# -eq 0 ]; then
        echo "Wolfies Executive Function Skill Installer"
        echo ""
        echo "Usage: $0 <skill-name>"
        echo ""
        echo "Available skills:"
        echo "  wolfies-imessage   - iMessage CLI with semantic search (19x faster than MCP)"
        echo "  wolfies-gmail      - Gmail MCP server for Claude Code"
        echo "  wolfies-calendar   - Google Calendar MCP server for Claude Code"
        echo "  wolfies-reminders  - Apple Reminders MCP server for Claude Code"
        echo "  all                - Install all skills"
        echo ""
        echo "Example:"
        echo "  $0 wolfies-imessage"
        echo "  $0 all"
        exit 0
    fi

    local skill_name=$1

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Wolfies Executive Function Skill Installer             ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    check_dependencies
    ensure_tap

    mkdir -p "$SKILLS_DIR"

    install_skill "$skill_name"

    log_success "Installation complete!"
}

main "$@"
