#!/bin/bash
# Install Claude Code plugins from project's local marketplace

set -e

MARKETPLACE_NAME="knowledge-finder-bot-plugins"
MARKETPLACE_PATH="./.claude/plugins"
PLUGIN_NAME="update-knowledge-bot-docs"

echo "Installing Claude Code plugins..."

# Check if running from project root
if [ ! -f "$MARKETPLACE_PATH/.claude-plugin/marketplace.json" ]; then
    echo "Error: Marketplace not found at $MARKETPLACE_PATH"
    echo "Make sure you're running this from the project root directory."
    exit 1
fi

# Check if claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "Error: 'claude' CLI not found."
    echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

# Step 1: Register local marketplace (idempotent - skips if already added)
echo "Registering local marketplace..."
if claude plugin marketplace list 2>&1 | grep -q "$MARKETPLACE_NAME"; then
    echo "Marketplace '$MARKETPLACE_NAME' already registered, updating..."
    claude plugin marketplace update "$MARKETPLACE_NAME"
else
    claude plugin marketplace add "$MARKETPLACE_PATH"
fi

# Step 2: Install plugin
echo "Installing $PLUGIN_NAME plugin..."
if claude plugin list 2>&1 | grep -q "$PLUGIN_NAME@$MARKETPLACE_NAME"; then
    echo "Plugin already installed, updating..."
    claude plugin update "$PLUGIN_NAME@$MARKETPLACE_NAME"
else
    claude plugin install "$PLUGIN_NAME@$MARKETPLACE_NAME" --scope user
fi

# Step 3: Enable plugin
echo "Enabling $PLUGIN_NAME plugin..."
claude plugin enable "$PLUGIN_NAME@$MARKETPLACE_NAME"

echo ""
echo "Plugin installed successfully!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code"
echo "2. Verify: /help | grep update-knowledge-bot-docs"
echo "3. Use: /update-knowledge-bot-docs"
