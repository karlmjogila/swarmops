# HL-Bot MCP Server

MCP (Model Context Protocol) server for HL-Bot, enabling Claude Desktop integration for trading analysis.

## Overview

This MCP server allows you to use Claude Desktop (with your Claude Max subscription) to:
- Analyze trading content (PDFs, videos, YouTube)
- Extract and create trading strategies
- Analyze chart images for patterns and signals

```
┌──────────────────┐         ┌───────────────────┐         ┌────────────────┐
│  Claude Desktop  │◄──MCP──►│  HL-Bot MCP       │◄──HTTP──►│  HL-Bot API   │
│  (Claude Max)    │         │  Server           │         │  (FastAPI)     │
└──────────────────┘         └───────────────────┘         └────────────────┘
```

## Installation

### Prerequisites

- Node.js 18+
- HL-Bot API running (default: http://localhost:3001)
- Claude Desktop installed

### Build

```bash
# From the monorepo root
pnpm install
pnpm --filter @hl-bot/mcp-server build

# Or from this package directory
cd packages/mcp-server
npm install
npm run build
```

### Claude Desktop Configuration

1. **Find your Claude Desktop config file:**
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/claude/claude_desktop_config.json`

2. **Add the HL-Bot MCP server configuration:**

```json
{
  "mcpServers": {
    "hl-bot": {
      "command": "node",
      "args": ["/path/to/hl-bot-v8/packages/mcp-server/dist/index.js"],
      "env": {
        "HL_BOT_API_URL": "http://localhost:3001",
        "HL_BOT_API_KEY": "your-api-key-if-needed"
      }
    }
  }
}
```

**Or using npx (after publishing):**

```json
{
  "mcpServers": {
    "hl-bot": {
      "command": "npx",
      "args": ["-y", "@hl-bot/mcp-server"],
      "env": {
        "HL_BOT_API_URL": "http://localhost:3001"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

## Available Tools

### `analyze-content`

Analyze uploaded trading content (PDF/video/YouTube).

**Parameters:**
- `contentId` (required): UUID of the content to analyze
- `includeTranscript` (optional): Whether to include full transcript

**Example prompt:**
> "Analyze the content with ID 123e4567-e89b-12d3-a456-426614174000"

### `extract-strategy`

Extract or create trading strategies.

**Modes:**
- `list`: List existing strategies
- `extract`: Get content details for strategy extraction
- `create`: Create a new strategy

**Example prompts:**
> "List all my trading strategies"
>
> "Extract a strategy from content ID 123e4567-..."
>
> "Create a new strategy called 'RSI Divergence' with entry on RSI crossing above 30 and exit at RSI above 70"

### `analyze-chart`

Analyze chart images for patterns and trading opportunities.

**Parameters:**
- `imageData` (required): Base64-encoded image
- `mimeType` (optional): Image MIME type
- `symbol` (optional): Trading pair (e.g., "BTC/USD")
- `timeframe` (optional): Chart timeframe (e.g., "4h")
- `focusAreas` (optional): Areas to focus on (patterns, structure, levels, indicators)

**Example prompts:**
> "Analyze this BTC/USD 4h chart for patterns and key levels"
>
> [Paste chart image] "What patterns do you see in this chart?"

## Available Resources

### `hlbot://strategies`

List of all trading strategies in HL-Bot.

### `hlbot://content`

List of all processed content (PDFs, videos) in HL-Bot.

**Example prompt:**
> "Show me my HL-Bot strategies"

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HL_BOT_API_URL` | HL-Bot API base URL | `http://localhost:3001` |
| `HL_BOT_API_KEY` | API authentication key | (none) |
| `HL_BOT_API_TIMEOUT` | API request timeout (ms) | `60000` |

## Development

### Running locally

```bash
# Development mode with hot reload
pnpm dev

# Or test the built version
pnpm build
node dist/index.js
```

### Testing with MCP Inspector

```bash
# Install MCP inspector globally
npm install -g @modelcontextprotocol/inspector

# Run inspector with the server
mcp-inspector node dist/index.js
```

## Troubleshooting

### Server not appearing in Claude Desktop

1. Check the config file path is correct
2. Verify the path to `dist/index.js` is absolute
3. Check Claude Desktop logs for errors
4. Restart Claude Desktop after config changes

### API connection errors

1. Ensure HL-Bot API is running
2. Check `HL_BOT_API_URL` is correct
3. Verify API key if authentication is enabled
4. Check network/firewall settings

### Image analysis not working

1. Ensure the image is properly base64-encoded
2. Check MIME type matches the actual image format
3. Verify image is a valid chart (candlestick/OHLC)

## Architecture

```
packages/mcp-server/
├── src/
│   └── index.ts       # Main MCP server entry point
├── dist/              # Compiled JavaScript
├── package.json
├── tsconfig.json
└── README.md
```

The server uses:
- **@modelcontextprotocol/sdk**: Official MCP SDK for server implementation
- **StdioServerTransport**: Communication via stdin/stdout (required for Claude Desktop)
- **Zod**: Schema validation for tool parameters

## Security Notes

- The MCP server runs locally on your machine
- API keys are passed via environment variables (not hardcoded)
- All API communication is HTTP (use HTTPS in production)
- Claude Desktop sandboxes MCP servers for additional security

## License

MIT
