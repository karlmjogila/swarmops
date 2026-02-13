#!/usr/bin/env node
/**
 * HL-Bot MCP Server
 *
 * This MCP server allows Claude Desktop to interact with HL-Bot's trading analysis
 * capabilities through the Model Context Protocol.
 *
 * Architecture:
 *   Claude Desktop <--MCP--> HL-Bot MCP Server <--> HL-Bot API
 *
 * Tools provided:
 *   - analyze-content: Analyze uploaded content (PDF/video/YouTube)
 *   - extract-strategy: Extract trading strategy from analyzed content
 *   - analyze-chart: Analyze chart images for patterns and structure
 *
 * Usage:
 *   Set HL_BOT_API_URL and optionally HL_BOT_API_KEY in environment
 *   Run: node dist/index.js (or use with Claude Desktop)
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import type { CallToolResult, ReadResourceResult } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { config } from 'dotenv';

// Load environment variables
config();

// Configuration
const API_URL = process.env.HL_BOT_API_URL || 'http://localhost:3001';
const API_KEY = process.env.HL_BOT_API_KEY || '';
const API_TIMEOUT = parseInt(process.env.HL_BOT_API_TIMEOUT || '60000', 10);

/**
 * HTTP client for HL-Bot API
 */
class HLBotApiClient {
  private baseUrl: string;
  private apiKey: string;
  private timeout: number;

  constructor(baseUrl: string, apiKey: string, timeout: number = 60000) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.timeout = timeout;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (this.apiKey) {
        headers['Authorization'] = `Bearer ${this.apiKey}`;
      }

      const response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`API error (${response.status}): ${error}`);
      }

      return response.json() as Promise<T>;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async getContent(contentId: string) {
    return this.request<{ data: ContentRecord }>('GET', `/api/v1/content/${contentId}`);
  }

  async listContent(params: { status?: string; type?: string; limit?: number } = {}) {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.type) query.set('type', params.type);
    if (params.limit) query.set('limit', params.limit.toString());

    const queryStr = query.toString();
    return this.request<{ data: ContentRecord[]; meta: { total: number } }>(
      'GET',
      `/api/v1/content${queryStr ? `?${queryStr}` : ''}`
    );
  }

  async getStrategy(strategyId: string) {
    return this.request<{ data: StrategyRecord }>('GET', `/api/v1/strategies/${strategyId}`);
  }

  async listStrategies(params: { status?: string; limit?: number } = {}) {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.limit) query.set('limit', params.limit.toString());

    const queryStr = query.toString();
    return this.request<{ data: StrategyRecord[]; meta: { total: number } }>(
      'GET',
      `/api/v1/strategies${queryStr ? `?${queryStr}` : ''}`
    );
  }

  async createStrategy(strategy: CreateStrategyRequest) {
    return this.request<{ data: StrategyRecord }>('POST', '/api/v1/strategies', strategy);
  }

  async healthCheck() {
    return this.request<{ status: string }>('GET', '/api/v1/health');
  }
}

// Types for API responses
interface ContentRecord {
  id: string;
  userId: string;
  type: 'pdf' | 'video' | 'youtube' | 'image';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  sourceUrl?: string;
  progress: number;
  error?: string;
  artifacts?: {
    transcript?: string;
    extractedText?: string;
    summary?: string;
    keyPoints?: string[];
    tradingInsights?: string[];
  };
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

interface StrategyRecord {
  id: string;
  userId: string;
  name: string;
  description?: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'archived';
  rules?: StrategyRule[];
  entryConditions?: Condition[];
  exitConditions?: Condition[];
  riskParameters?: RiskParameters;
  timeframes?: string[];
  requiredPatterns?: string[];
  confidence?: number;
  reasoning?: string;
  contentId?: string;
  createdAt: string;
  updatedAt: string;
}

interface StrategyRule {
  type: 'entry' | 'exit' | 'filter' | 'risk';
  conditions: Condition[];
  logic: 'AND' | 'OR';
  description?: string;
}

interface Condition {
  indicator: string;
  operator: string;
  value?: unknown;
  timeframe?: string;
  metadata?: Record<string, unknown>;
}

interface RiskParameters {
  maxPositionSizePct?: number;
  defaultStopLossPct?: number;
  defaultTakeProfitPct?: number;
  maxDailyLossPct?: number;
  maxOpenPositions?: number;
  riskRewardRatio?: number;
}

interface CreateStrategyRequest {
  name: string;
  description?: string;
  rules?: StrategyRule[];
  entryConditions?: Condition[];
  exitConditions?: Condition[];
  riskParameters?: RiskParameters;
  timeframes?: string[];
  requiredPatterns?: string[];
  confidence?: number;
  reasoning?: string;
  contentId?: string;
}

// Initialize API client
const apiClient = new HLBotApiClient(API_URL, API_KEY, API_TIMEOUT);

// Create MCP server
const server = new McpServer(
  {
    name: 'hl-bot-mcp-server',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// ============================================================================
// Tool: analyze-content
// ============================================================================
server.registerTool(
  'analyze-content',
  {
    title: 'Analyze Content',
    description: `Analyze uploaded trading content (PDF, video, or YouTube).

This tool retrieves content that has been processed by HL-Bot and returns
the extracted information including transcripts, summaries, and trading insights.

Use this to:
- Review processed trading education material
- Get summaries and key points from videos/PDFs
- Extract trading-related insights

The content must first be uploaded through the HL-Bot web interface.`,
    inputSchema: {
      contentId: z.string().uuid().describe('The UUID of the content to analyze'),
      includeTranscript: z
        .boolean()
        .optional()
        .default(false)
        .describe('Whether to include the full transcript/text (can be long)'),
    },
  },
  async ({ contentId, includeTranscript }): Promise<CallToolResult> => {
    try {
      const result = await apiClient.getContent(contentId);
      const content = result.data;

      if (content.status === 'processing') {
        return {
          content: [
            {
              type: 'text',
              text: `Content is still being processed (${content.progress}% complete). Please try again later.`,
            },
          ],
        };
      }

      if (content.status === 'failed') {
        return {
          content: [
            {
              type: 'text',
              text: `Content processing failed: ${content.error || 'Unknown error'}`,
            },
          ],
          isError: true,
        };
      }

      if (content.status === 'pending') {
        return {
          content: [
            {
              type: 'text',
              text: 'Content is pending processing. Please try again later.',
            },
          ],
        };
      }

      // Build response for completed content
      const parts: string[] = [];
      parts.push(`## Content Analysis: ${content.type.toUpperCase()}`);
      parts.push(`**ID:** ${content.id}`);
      parts.push(`**Status:** ${content.status}`);
      if (content.sourceUrl) {
        parts.push(`**Source:** ${content.sourceUrl}`);
      }
      parts.push(`**Created:** ${content.createdAt}`);
      parts.push('');

      const artifacts = content.artifacts;
      if (artifacts) {
        if (artifacts.summary) {
          parts.push('### Summary');
          parts.push(artifacts.summary);
          parts.push('');
        }

        if (artifacts.keyPoints && artifacts.keyPoints.length > 0) {
          parts.push('### Key Points');
          for (const point of artifacts.keyPoints) {
            parts.push(`- ${point}`);
          }
          parts.push('');
        }

        if (artifacts.tradingInsights && artifacts.tradingInsights.length > 0) {
          parts.push('### Trading Insights');
          for (const insight of artifacts.tradingInsights) {
            parts.push(`- ${insight}`);
          }
          parts.push('');
        }

        if (includeTranscript) {
          const text = artifacts.transcript || artifacts.extractedText;
          if (text) {
            parts.push('### Full Transcript/Text');
            parts.push(text);
          }
        }
      }

      return {
        content: [{ type: 'text', text: parts.join('\n') }],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        content: [{ type: 'text', text: `Error analyzing content: ${message}` }],
        isError: true,
      };
    }
  }
);

// ============================================================================
// Tool: extract-strategy
// ============================================================================
server.registerTool(
  'extract-strategy',
  {
    title: 'Extract Trading Strategy',
    description: `Extract or create a trading strategy from analyzed content.

This tool helps you:
1. Extract strategies from processed content (PDFs, videos)
2. Create new strategies with defined rules
3. Link strategies to source content

Strategies include:
- Entry/exit conditions with specific indicators
- Risk parameters (stop loss, take profit, position sizing)
- Required patterns and timeframes
- Confidence scores and reasoning

Created strategies are stored in HL-Bot for backtesting and live trading.`,
    inputSchema: {
      mode: z
        .enum(['extract', 'create', 'list'])
        .describe('Operation mode: extract from content, create new, or list existing'),
      contentId: z
        .string()
        .uuid()
        .optional()
        .describe('Content ID to extract strategy from (for extract mode)'),
      strategy: z
        .object({
          name: z.string().min(1).max(200).describe('Strategy name'),
          description: z.string().max(2000).optional().describe('Strategy description'),
          timeframes: z
            .array(z.string())
            .optional()
            .describe('Trading timeframes (e.g., ["1h", "4h", "1d"])'),
          entryConditions: z
            .array(
              z.object({
                indicator: z.string().describe('Indicator name (e.g., RSI, MACD, price)'),
                operator: z
                  .string()
                  .describe('Comparison operator (e.g., crosses_above, greater)'),
                value: z.unknown().describe('Target value'),
                timeframe: z.string().optional().describe('Specific timeframe for this condition'),
              })
            )
            .optional()
            .describe('Entry conditions'),
          exitConditions: z
            .array(
              z.object({
                indicator: z.string(),
                operator: z.string(),
                value: z.unknown(),
                timeframe: z.string().optional(),
              })
            )
            .optional()
            .describe('Exit conditions'),
          riskParameters: z
            .object({
              maxPositionSizePct: z.number().positive().max(100).optional(),
              defaultStopLossPct: z.number().positive().max(100).optional(),
              defaultTakeProfitPct: z.number().positive().optional(),
              maxDailyLossPct: z.number().positive().max(100).optional(),
              maxOpenPositions: z.number().int().positive().optional(),
              riskRewardRatio: z.number().positive().optional(),
            })
            .optional()
            .describe('Risk management parameters'),
          requiredPatterns: z
            .array(z.string())
            .optional()
            .describe('Required chart patterns (e.g., ["head_shoulders", "double_bottom"])'),
          confidence: z.number().min(0).max(1).optional().describe('Confidence score 0-1'),
          reasoning: z.string().max(5000).optional().describe('Reasoning behind the strategy'),
        })
        .optional()
        .describe('Strategy definition (for create mode)'),
      limit: z.number().int().min(1).max(50).optional().default(10).describe('Max results for list mode'),
    },
  },
  async ({ mode, contentId, strategy, limit }): Promise<CallToolResult> => {
    try {
      if (mode === 'list') {
        const result = await apiClient.listStrategies({ limit });
        const strategies = result.data;

        if (strategies.length === 0) {
          return {
            content: [{ type: 'text', text: 'No strategies found.' }],
          };
        }

        const parts: string[] = ['## Strategies', ''];
        for (const s of strategies) {
          parts.push(`### ${s.name}`);
          parts.push(`- **ID:** ${s.id}`);
          parts.push(`- **Status:** ${s.status}`);
          if (s.description) parts.push(`- **Description:** ${s.description}`);
          if (s.timeframes) parts.push(`- **Timeframes:** ${s.timeframes.join(', ')}`);
          if (s.confidence !== undefined)
            parts.push(`- **Confidence:** ${(s.confidence * 100).toFixed(0)}%`);
          parts.push('');
        }

        return {
          content: [{ type: 'text', text: parts.join('\n') }],
        };
      }

      if (mode === 'extract') {
        if (!contentId) {
          return {
            content: [{ type: 'text', text: 'contentId is required for extract mode' }],
            isError: true,
          };
        }

        // Get the content first
        const contentResult = await apiClient.getContent(contentId);
        const content = contentResult.data;

        if (content.status !== 'completed') {
          return {
            content: [
              {
                type: 'text',
                text: `Cannot extract strategy: content status is "${content.status}". Content must be completed first.`,
              },
            ],
            isError: true,
          };
        }

        // Return the content analysis for Claude to process
        const artifacts = content.artifacts;
        const parts: string[] = [
          '## Content Ready for Strategy Extraction',
          '',
          `**Content ID:** ${content.id}`,
          `**Type:** ${content.type}`,
          '',
        ];

        if (artifacts?.summary) {
          parts.push('### Summary');
          parts.push(artifacts.summary);
          parts.push('');
        }

        if (artifacts?.tradingInsights && artifacts.tradingInsights.length > 0) {
          parts.push('### Trading Insights Found');
          for (const insight of artifacts.tradingInsights) {
            parts.push(`- ${insight}`);
          }
          parts.push('');
        }

        parts.push('---');
        parts.push('');
        parts.push(
          'Please analyze the above content and use the `extract-strategy` tool with mode="create" to define a strategy based on these insights.'
        );
        parts.push('');
        parts.push('Include:');
        parts.push('- Clear entry and exit conditions');
        parts.push('- Risk parameters (stop loss, take profit, position size)');
        parts.push('- Required patterns or indicators');
        parts.push('- Timeframes');
        parts.push(`- Reference this content ID: ${contentId}`);

        return {
          content: [{ type: 'text', text: parts.join('\n') }],
        };
      }

      if (mode === 'create') {
        if (!strategy || !strategy.name) {
          return {
            content: [{ type: 'text', text: 'strategy with name is required for create mode' }],
            isError: true,
          };
        }

        const createRequest: CreateStrategyRequest = {
          name: strategy.name,
          description: strategy.description,
          entryConditions: strategy.entryConditions,
          exitConditions: strategy.exitConditions,
          riskParameters: strategy.riskParameters,
          timeframes: strategy.timeframes,
          requiredPatterns: strategy.requiredPatterns,
          confidence: strategy.confidence,
          reasoning: strategy.reasoning,
          contentId: contentId,
        };

        const result = await apiClient.createStrategy(createRequest);
        const created = result.data;

        const parts: string[] = [
          '## Strategy Created Successfully',
          '',
          `**Name:** ${created.name}`,
          `**ID:** ${created.id}`,
          `**Status:** ${created.status}`,
          '',
        ];

        if (created.description) {
          parts.push(`**Description:** ${created.description}`);
        }

        if (created.timeframes && created.timeframes.length > 0) {
          parts.push(`**Timeframes:** ${created.timeframes.join(', ')}`);
        }

        if (created.entryConditions && created.entryConditions.length > 0) {
          parts.push('');
          parts.push('### Entry Conditions');
          for (const cond of created.entryConditions) {
            parts.push(`- ${cond.indicator} ${cond.operator} ${JSON.stringify(cond.value)}`);
          }
        }

        if (created.exitConditions && created.exitConditions.length > 0) {
          parts.push('');
          parts.push('### Exit Conditions');
          for (const cond of created.exitConditions) {
            parts.push(`- ${cond.indicator} ${cond.operator} ${JSON.stringify(cond.value)}`);
          }
        }

        if (created.riskParameters) {
          parts.push('');
          parts.push('### Risk Parameters');
          const rp = created.riskParameters;
          if (rp.defaultStopLossPct) parts.push(`- Stop Loss: ${rp.defaultStopLossPct}%`);
          if (rp.defaultTakeProfitPct) parts.push(`- Take Profit: ${rp.defaultTakeProfitPct}%`);
          if (rp.maxPositionSizePct) parts.push(`- Max Position Size: ${rp.maxPositionSizePct}%`);
          if (rp.riskRewardRatio) parts.push(`- Risk/Reward Ratio: ${rp.riskRewardRatio}`);
        }

        parts.push('');
        parts.push('The strategy has been saved and can now be backtested or used for live trading.');

        return {
          content: [{ type: 'text', text: parts.join('\n') }],
        };
      }

      return {
        content: [{ type: 'text', text: `Unknown mode: ${mode}` }],
        isError: true,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        content: [{ type: 'text', text: `Error in extract-strategy: ${message}` }],
        isError: true,
      };
    }
  }
);

// ============================================================================
// Tool: analyze-chart
// ============================================================================
server.registerTool(
  'analyze-chart',
  {
    title: 'Analyze Chart Image',
    description: `Analyze a trading chart image for patterns, structure, and trading opportunities.

This tool accepts a base64-encoded chart image and returns analysis including:
- Detected chart patterns (head & shoulders, triangles, etc.)
- Market structure (trends, support/resistance)
- Key price levels
- Potential trading signals

The image should be a candlestick or OHLC chart from any trading platform.

Note: This tool prepares the image for analysis. For complex AI-based analysis,
Claude will process the image directly.`,
    inputSchema: {
      imageData: z
        .string()
        .describe('Base64-encoded image data (PNG, JPEG, WebP supported)'),
      mimeType: z
        .enum(['image/png', 'image/jpeg', 'image/webp'])
        .optional()
        .default('image/png')
        .describe('MIME type of the image'),
      symbol: z.string().optional().describe('Trading symbol/pair (e.g., BTC/USD, ETH/USDT)'),
      timeframe: z
        .string()
        .optional()
        .describe('Chart timeframe (e.g., 1h, 4h, 1d)'),
      focusAreas: z
        .array(z.enum(['patterns', 'structure', 'levels', 'indicators', 'all']))
        .optional()
        .default(['all'])
        .describe('Specific areas to focus analysis on'),
    },
  },
  async ({ imageData, mimeType, symbol, timeframe, focusAreas }): Promise<CallToolResult> => {
    try {
      // Validate base64 data
      const cleanedData = imageData.replace(/^data:image\/[a-z]+;base64,/, '');

      // Basic validation - check if it looks like valid base64
      if (!/^[A-Za-z0-9+/]+=*$/.test(cleanedData.replace(/\s/g, ''))) {
        return {
          content: [{ type: 'text', text: 'Invalid image data: not valid base64 encoding' }],
          isError: true,
        };
      }

      // Build analysis request context
      const context: string[] = ['## Chart Analysis Request', ''];

      if (symbol) context.push(`**Symbol:** ${symbol}`);
      if (timeframe) context.push(`**Timeframe:** ${timeframe}`);
      context.push(`**Focus Areas:** ${focusAreas?.join(', ') || 'all'}`);
      context.push('');

      // Return the image as content for Claude to analyze
      const analysisPrompt = [
        'Please analyze this trading chart image and provide:',
        '',
        focusAreas?.includes('all') || focusAreas?.includes('patterns')
          ? '1. **Chart Patterns:** Identify any recognizable patterns (head & shoulders, triangles, wedges, flags, double tops/bottoms, etc.)'
          : '',
        focusAreas?.includes('all') || focusAreas?.includes('structure')
          ? '2. **Market Structure:** Determine the trend direction, identify higher highs/lows or lower highs/lows, and any break of structure (BOS) or change of character (CHoCH)'
          : '',
        focusAreas?.includes('all') || focusAreas?.includes('levels')
          ? '3. **Key Levels:** Identify significant support and resistance levels, and any order blocks or supply/demand zones'
          : '',
        focusAreas?.includes('all') || focusAreas?.includes('indicators')
          ? '4. **Indicator Analysis:** If visible, analyze any technical indicators (RSI, MACD, moving averages, etc.)'
          : '',
        '',
        '5. **Trading Implications:** Based on your analysis, suggest potential:',
        '   - Entry points and direction (long/short)',
        '   - Stop loss levels',
        '   - Take profit targets',
        '   - Risk/reward assessment',
      ]
        .filter(Boolean)
        .join('\n');

      context.push(analysisPrompt);

      return {
        content: [
          { type: 'text', text: context.join('\n') },
          {
            type: 'image',
            data: cleanedData,
            mimeType: mimeType || 'image/png',
          },
        ],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        content: [{ type: 'text', text: `Error analyzing chart: ${message}` }],
        isError: true,
      };
    }
  }
);

// ============================================================================
// Resource: strategies
// ============================================================================
server.registerResource(
  'strategies-list',
  'hlbot://strategies',
  {
    title: 'Trading Strategies',
    description: 'List of all trading strategies in HL-Bot',
    mimeType: 'application/json',
  },
  async (): Promise<ReadResourceResult> => {
    try {
      const result = await apiClient.listStrategies({ limit: 50 });
      return {
        contents: [
          {
            uri: 'hlbot://strategies',
            mimeType: 'application/json',
            text: JSON.stringify(result.data, null, 2),
          },
        ],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        contents: [
          {
            uri: 'hlbot://strategies',
            mimeType: 'text/plain',
            text: `Error fetching strategies: ${message}`,
          },
        ],
      };
    }
  }
);

// ============================================================================
// Resource: content
// ============================================================================
server.registerResource(
  'content-list',
  'hlbot://content',
  {
    title: 'Processed Content',
    description: 'List of all processed content (PDFs, videos) in HL-Bot',
    mimeType: 'application/json',
  },
  async (): Promise<ReadResourceResult> => {
    try {
      const result = await apiClient.listContent({ limit: 50 });
      return {
        contents: [
          {
            uri: 'hlbot://content',
            mimeType: 'application/json',
            text: JSON.stringify(result.data, null, 2),
          },
        ],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        contents: [
          {
            uri: 'hlbot://content',
            mimeType: 'text/plain',
            text: `Error fetching content: ${message}`,
          },
        ],
      };
    }
  }
);

// ============================================================================
// Main: Start the server
// ============================================================================
async function main() {
  // Test API connection (optional, non-blocking)
  try {
    await apiClient.healthCheck();
    console.error('[HL-Bot MCP] Connected to API at', API_URL);
  } catch (error) {
    console.error('[HL-Bot MCP] Warning: Could not connect to API at', API_URL);
    console.error('[HL-Bot MCP] Some features may not work until the API is available');
  }

  // Create stdio transport
  const transport = new StdioServerTransport();

  // Connect server to transport
  await server.connect(transport);

  console.error('[HL-Bot MCP] Server started');
}

main().catch((error) => {
  console.error('[HL-Bot MCP] Fatal error:', error);
  process.exit(1);
});
