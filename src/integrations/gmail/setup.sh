#!/bin/bash
# Gmail MCP Server Setup Script

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CREDENTIALS_DIR="$PROJECT_ROOT/config/google_credentials"

echo "=== Gmail MCP Server Setup ==="
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Credentials Dir: $CREDENTIALS_DIR"
echo ""

# Step 1: Create directories
echo "[1/5] Creating directories..."
mkdir -p "$CREDENTIALS_DIR"
mkdir -p "$PROJECT_ROOT/logs"
echo "✓ Directories created"
echo ""

# Step 2: Install Python dependencies
echo "[2/5] Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"
echo ""

# Step 3: Check for credentials
echo "[3/5] Checking for Google credentials..."
if [ ! -f "$CREDENTIALS_DIR/credentials.json" ]; then
    echo "⚠ credentials.json not found!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Go to https://console.cloud.google.com"
    echo "2. Create a new project (or select existing)"
    echo "3. Enable Gmail API"
    echo "4. Create OAuth 2.0 Client ID (Desktop app)"
    echo "5. Download credentials.json"
    echo "6. Save it to: $CREDENTIALS_DIR/credentials.json"
    echo ""
    read -p "Press Enter after you've placed credentials.json in the correct location..."
fi

if [ -f "$CREDENTIALS_DIR/credentials.json" ]; then
    echo "✓ credentials.json found"
else
    echo "✗ credentials.json still not found. Setup incomplete."
    exit 1
fi
echo ""

# Step 4: Register MCP server
echo "[4/5] Registering MCP server with Claude Code..."
echo "Command: claude mcp add -t stdio gmail -- python3 $SCRIPT_DIR/server.py"
echo ""
read -p "Register now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    claude mcp add -t stdio gmail -- python3 "$SCRIPT_DIR/server.py"
    echo "✓ MCP server registered"
else
    echo "⚠ Skipped MCP registration. You can register manually later:"
    echo "  claude mcp add -t stdio gmail -- python3 $SCRIPT_DIR/server.py"
fi
echo ""

# Step 5: Verify setup
echo "[5/5] Verifying setup..."
if command -v claude &> /dev/null; then
    echo "Registered MCP servers:"
    claude mcp list
else
    echo "⚠ Claude Code CLI not found. Install from https://claude.ai/code"
fi
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Use Gmail tools in Claude Code"
echo "2. First use will trigger OAuth flow in browser"
echo "3. Token will be saved to $CREDENTIALS_DIR/gmail_token.pickle"
echo ""
echo "Example commands:"
echo "  - \"Check my email\""
echo "  - \"Show unread emails\""
echo "  - \"Send an email to someone@example.com\""
echo ""
echo "For troubleshooting, check: $PROJECT_ROOT/logs/gmail.log"
echo ""
