#!/bin/bash
# Launch script for Hyperliquid MCP Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: .env file not found"
    echo "Copy .env.mcp.example to .env and configure it"
    exit 1
fi

# Check for required variables
if [ -z "$HYPERLIQUID_PRIVATE_KEY" ]; then
    echo "❌ Error: HYPERLIQUID_PRIVATE_KEY not set"
    echo "Set it in .env file"
    exit 1
fi

# Display configuration
echo "================================================"
echo "Hyperliquid MCP Server"
echo "================================================"
echo "Network: ${HYPERLIQUID_TESTNET:-true}"
echo "Paper Mode: ${HYPERLIQUID_PAPER_MODE:-true}"
echo "Log Level: ${LOG_LEVEL:-info}"
echo "================================================"

# Safety warning
if [ "${HYPERLIQUID_PAPER_MODE}" == "false" ]; then
    echo ""
    echo "⚠️⚠️⚠️  WARNING: LIVE TRADING MODE ENABLED  ⚠️⚠️⚠️"
    echo "Real funds are at risk!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo "Starting MCP server..."
echo "Press Ctrl+C to stop"
echo ""

# Run the server
poetry run python -m hl_bot.trading.mcp_server
