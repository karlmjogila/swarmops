---
name: llm-integration
description: >
  Build production-grade LLM-powered applications with proper prompt design, structured
  output parsing, tool use, error handling, cost optimization, and evaluation patterns.
  Covers Anthropic Claude API, prompt engineering, agent architectures, RAG patterns,
  and AI safety guardrails. Trigger this skill for any task involving LLM APIs, Claude
  integration, prompt engineering, AI agents, tool use, structured outputs, embeddings,
  or any AI/ML service integration.
triggers:
  - llm
  - claude
  - anthropic
  - openai
  - gpt
  - prompt
  - ai
  - agent
  - rag
  - embedding
  - vector
  - completion
  - chat
  - model
  - inference
  - token
  - context window
  - fine-tune
  - tool use
  - function calling
  - structured output
  - retrieval
  - chunk
  - pgvector
  - pinecone
  - langchain
  - memory
  - multi-turn
---

# LLM Integration Excellence

LLMs are powerful but unpredictable. Build integrations that are robust against the inherent non-determinism of language models. Validate outputs, handle failures gracefully, manage costs, and never trust model output without verification for critical operations.

## Core Principles

1. **Validate, don't trust** — LLM outputs are suggestions, not facts. Always validate structured outputs against schemas.
2. **Prompt is code** — Version, test, and review prompts. A prompt change is a behavior change.
3. **Cost is a feature** — Cache aggressively, choose the right model for the task, measure cost per operation.
4. **Config over constants** — API keys in env vars, model selection via config (12-Factor, Factor III).
5. **Test before you change** — Write eval tests before modifying prompts (TDD for prompts).

## Client Setup (Anthropic SDK)

```python
# Python
from anthropic import AsyncAnthropic, APIError, RateLimitError
import os

client = AsyncAnthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],  # 12-Factor III
    max_retries=3, timeout=120.0,
)

LLM_CONFIG = {
    "fast": os.getenv("LLM_MODEL_FAST", "claude-haiku-4-5-20251001"),
    "balanced": os.getenv("LLM_MODEL_BALANCED", "claude-sonnet-4-5-20250929"),
    "powerful": os.getenv("LLM_MODEL_POWERFUL", "claude-opus-4-6"),
}
```
```typescript
// TypeScript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
  maxRetries: 3,
  timeout: 120_000,
});
```

## Calling the API

```python
# Python
async def generate_response(
    system_prompt: str, user_message: str,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4096, temperature: float = 0.0,
) -> str:
    try:
        response = await client.messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except RateLimitError:
        logger.error("Rate limited after all retries"); raise
    except APIError as e:
        logger.error("API error", status=e.status_code); raise
```
```typescript
// TypeScript
async function generateResponse(
  systemPrompt: string, userMessage: string,
  model = "claude-sonnet-4-5-20250929", maxTokens = 4096, temperature = 0.0,
): Promise<string> {
  const response = await client.messages.create({
    model, max_tokens: maxTokens, temperature,
    system: systemPrompt,
    messages: [{ role: "user", content: userMessage }],
  });
  const block = response.content[0];
  if (block.type === "text") return block.text;
  throw new Error(`Unexpected block type: ${block.type}`);
}
```

## Prompt Engineering

```python
ANALYSIS_PROMPT = """You are a financial analyst specializing in cryptocurrency markets.

## Context
You are analyzing trading data for a portfolio management system.

## Task
Analyze the market data and provide: sentiment, support/resistance levels, risk assessment.

## Format
Respond in JSON: {"sentiment": "bullish|bearish|neutral", "support_levels": [float], "resistance_levels": [float], "risk": "low|medium|high", "reasoning": "string"}

## Constraints
- Base analysis ONLY on provided data — do not hallucinate price levels
- If data is insufficient, set risk to "high" and explain in reasoning
"""

class PromptManager:
    """Load prompts from files. Prompts are code — version them."""
    def __init__(self, prompts_dir: Path):
        self._dir = prompts_dir
        self._cache: dict[str, str] = {}

    def get(self, name: str, **kwargs) -> str:
        if name not in self._cache:
            self._cache[name] = (self._dir / f"{name}.txt").read_text()
        return Template(self._cache[name]).safe_substitute(**kwargs)
```

## Structured Outputs (Pydantic)

```python
# Python — Pydantic validation
from pydantic import BaseModel

class MarketAnalysis(BaseModel):
    sentiment: str
    support_levels: list[float]
    resistance_levels: list[float]
    risk: str
    reasoning: str

async def analyze_market(data: str) -> MarketAnalysis:
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929", max_tokens=2048,
        system=ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": f"Analyze:\n{data}"}],
    )
    try:
        return MarketAnalysis.model_validate_json(response.content[0].text)
    except Exception as e:
        raise ValueError(f"Invalid model output: {e}")

# Python — SDK guaranteed schema
from anthropic import transform_schema

async def analyze_with_schema(data: str) -> MarketAnalysis:
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929", max_tokens=2048, system=ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": f"Analyze:\n{data}"}],
        output_config={"format": {"type": "json_schema", "schema": transform_schema(MarketAnalysis)}},
    )
    return MarketAnalysis.model_validate_json(response.content[0].text)
```
```typescript
// TypeScript — Zod validation
import { z } from "zod";

const MarketAnalysisSchema = z.object({
  sentiment: z.enum(["bullish", "bearish", "neutral"]),
  support_levels: z.array(z.number()),
  resistance_levels: z.array(z.number()),
  risk: z.enum(["low", "medium", "high"]),
  reasoning: z.string(),
});

async function analyzeMarket(data: string) {
  const resp = await client.messages.create({
    model: "claude-sonnet-4-5-20250929", max_tokens: 2048, system: ANALYSIS_PROMPT,
    messages: [{ role: "user", content: `Analyze:\n${data}` }],
  });
  return MarketAnalysisSchema.parse(JSON.parse((resp.content[0] as Anthropic.TextBlock).text));
}
```

## Tool Use / Function Calling

```python
tools = [
    {"name": "get_market_price", "description": "Get current price for a trading pair", "strict": True,
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"], "additionalProperties": False}},
    {"name": "place_order", "description": "Place a trading order", "strict": True,
     "input_schema": {"type": "object", "properties": {
         "symbol": {"type": "string"}, "side": {"type": "string", "enum": ["buy", "sell"]},
         "quantity": {"type": "number"}, "order_type": {"type": "string", "enum": ["market", "limit"]},
         "price": {"type": "number"}},
      "required": ["symbol", "side", "quantity", "order_type"], "additionalProperties": False}},
]

async def run_agent_loop(user_message: str, tools: list[dict], max_iterations: int = 10) -> str:
    messages = [{"role": "user", "content": user_message}]
    for _ in range(max_iterations):
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929", max_tokens=4096,
            system="You are a trading assistant.", messages=messages, tools=tools,
        )
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await execute_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        elif response.stop_reason == "end_turn":
            return "\n".join(b.text for b in response.content if b.type == "text")
        elif response.stop_reason == "refusal":
            return "I cannot help with that request."
    return "Unable to complete the task within allowed steps."
```
```typescript
// TypeScript tool use loop
async function runAgentLoop(userMessage: string, tools: Anthropic.Tool[], maxIter = 10): Promise<string> {
  const messages: Anthropic.MessageParam[] = [{ role: "user", content: userMessage }];
  for (let i = 0; i < maxIter; i++) {
    const resp = await client.messages.create({
      model: "claude-sonnet-4-5-20250929", max_tokens: 4096, messages, tools,
    });
    if (resp.stop_reason === "tool_use") {
      const results: Anthropic.ToolResultBlockParam[] = [];
      for (const b of resp.content) {
        if (b.type === "tool_use") {
          const r = await executeTool(b.name, b.input as Record<string, unknown>);
          results.push({ type: "tool_result", tool_use_id: b.id, content: JSON.stringify(r) });
        }
      }
      messages.push({ role: "assistant", content: resp.content });
      messages.push({ role: "user", content: results });
    } else if (resp.stop_reason === "end_turn") {
      return resp.content.filter((b): b is Anthropic.TextBlock => b.type === "text").map(b => b.text).join("\n");
    }
  }
  return "Unable to complete within allowed steps.";
}
```

## Cost Optimization

```python
# claude-haiku-4-5  — Fast, cheap. Classification, extraction, simple Q&A
# claude-sonnet-4-5 — Balanced. Analysis, code gen, most tasks
# claude-opus-4-6   — Most capable. Complex reasoning, critical decisions
# Rule: start with cheapest model that works, upgrade only when needed
MODEL_FOR_TASK = {
    "classify_sentiment": LLM_CONFIG["fast"],
    "extract_entities": LLM_CONFIG["fast"],
    "analyze_market": LLM_CONFIG["balanced"],
    "generate_report": LLM_CONFIG["balanced"],
    "complex_reasoning": LLM_CONFIG["powerful"],
}
```

## Caching

```python
import hashlib, json

class LLMCache:
    """Cache deterministic LLM calls (temperature=0 only)."""
    def __init__(self):
        self._cache: dict[str, str] = {}

    def _key(self, model: str, messages: list, system: str = "") -> str:
        return hashlib.sha256(json.dumps({"model": model, "messages": messages, "system": system}).encode()).hexdigest()

    async def get_or_create(self, client, model, messages, system="", **kwargs) -> str:
        key = self._key(model, messages, system)
        if key in self._cache: return self._cache[key]
        resp = await client.messages.create(model=model, messages=messages, system=system, temperature=0, **kwargs)
        self._cache[key] = resp.content[0].text
        return self._cache[key]

# Anthropic prompt caching — cache large system prompts server-side
async def call_with_prompt_caching(user_message: str) -> str:
    """Min 1024 tokens for Sonnet/Opus, 2048 for Haiku."""
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929", max_tokens=4096,
        system=[{"type": "text", "text": LARGE_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
```

## Token Management

```python
async def count_tokens_exact(client, messages, model="claude-sonnet-4-5-20250929", **kw) -> int:
    return (await client.messages.count_tokens(model=model, messages=messages, **kw)).input_tokens

def estimate_tokens(text: str) -> int:
    return len(text) // 4  # ~4 chars per token for English

def truncate_to_fit(text: str, max_tokens: int, strategy: str = "tail") -> str:
    if estimate_tokens(text) <= max_tokens: return text
    c = max_tokens * 4
    if strategy == "tail": return "...[truncated]...\n" + text[-c:]
    if strategy == "head": return text[:c] + "\n...[truncated]..."
    return text[:c//2] + "\n...[truncated]...\n" + text[-c//2:]
```

## Context Window Management

```python
from dataclasses import dataclass

@dataclass
class ContextBudget:
    model_limit: int       # e.g. 200_000 for Claude Sonnet
    max_output_tokens: int
    system_tokens: int

    @property
    def available(self) -> int:
        return self.model_limit - self.max_output_tokens - self.system_tokens

def sliding_window_messages(messages: list[dict], budget: ContextBudget, keep_first: int = 1) -> list[dict]:
    """Pinned first messages + as many recent messages as fit."""
    pinned = messages[:keep_first]
    remaining = budget.available - sum(estimate_tokens(str(m)) for m in pinned)
    included = []
    for msg in reversed(messages[keep_first:]):
        t = estimate_tokens(str(msg))
        if remaining - t < 0: break
        included.insert(0, msg); remaining -= t
    return pinned + included

async def summarize_overflow(messages: list[dict]) -> list[dict]:
    """Summarize older messages that exceed the context window."""
    overflow, recent = messages[1:-10], messages[-10:]
    if not overflow: return messages
    summary = await generate_response(
        "Summarize concisely. Preserve key facts, decisions, open questions.",
        "\n".join(f"{m['role']}: {m['content']}" for m in overflow),
        model=LLM_CONFIG["fast"], max_tokens=1024,
    )
    return messages[:1] + [{"role": "user", "content": f"[Earlier summary]\n{summary}"}] + recent

# Priority-based selection
from enum import IntEnum

class ContextPriority(IntEnum):
    CRITICAL = 0  # System prompt, current query
    HIGH = 1      # Recent tool results
    MEDIUM = 2    # Older conversation
    LOW = 3       # Background material

@dataclass
class ContextItem:
    content: str
    priority: ContextPriority
    tokens: int

def select_context(items: list[ContextItem], budget: int) -> list[ContextItem]:
    selected, used = [], 0
    for item in sorted(items, key=lambda x: x.priority):
        if used + item.tokens <= budget: selected.append(item); used += item.tokens
    return selected
```

## Multi-Turn Conversations

```python
# Python
@dataclass
class Conversation:
    system_prompt: str
    messages: list[dict] = field(default_factory=list)
    model: str = "claude-sonnet-4-5-20250929"

    async def send(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        budget = ContextBudget(200_000, 4096, estimate_tokens(self.system_prompt))
        windowed = sliding_window_messages(self.messages, budget)
        resp = await client.messages.create(model=self.model, max_tokens=4096, system=self.system_prompt, messages=windowed)
        text = resp.content[0].text
        self.messages.append({"role": "assistant", "content": text})
        return text

async def compress_conversation(messages: list[dict], target_tokens: int = 2000) -> list[dict]:
    """Compress older turns, preserve most recent exchange."""
    if sum(estimate_tokens(str(m)) for m in messages) <= target_tokens: return messages
    preserved, to_compress = messages[-2:], messages[:-2]
    if not to_compress: return messages
    compressed = await generate_response(
        "Compress conversation. Keep: decisions, actions, facts, preferences. Drop: pleasantries.",
        "\n".join(f"{m['role']}: {m['content']}" for m in to_compress),
        model=LLM_CONFIG["fast"], max_tokens=target_tokens,
    )
    return [{"role": "user", "content": f"[Compressed]\n{compressed}"},
            {"role": "assistant", "content": "Understood, I have the earlier context."}, *preserved]
```
```typescript
// TypeScript
class Conversation {
  private messages: Anthropic.MessageParam[] = [];
  constructor(private systemPrompt: string, private model = "claude-sonnet-4-5-20250929", private maxMsgs = 50) {}

  async send(userMessage: string): Promise<string> {
    this.messages.push({ role: "user", content: userMessage });
    if (this.messages.length > this.maxMsgs) this.messages = this.messages.slice(-this.maxMsgs);
    const resp = await client.messages.create({
      model: this.model, max_tokens: 4096, system: this.systemPrompt, messages: this.messages,
    });
    const text = resp.content[0].type === "text" ? resp.content[0].text : "";
    this.messages.push({ role: "assistant", content: text });
    return text;
  }
}
```

## RAG (Retrieval-Augmented Generation)

### Document Chunking
```python
@dataclass
class Chunk:
    text: str
    metadata: dict
    token_count: int

def chunk_recursive(text: str, max_tokens: int = 512, overlap: int = 50, seps: list[str] | None = None) -> list[Chunk]:
    """Recursive split: headings -> paragraphs -> sentences -> words."""
    seps = seps or ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    if estimate_tokens(text) <= max_tokens:
        return [Chunk(text.strip(), {}, estimate_tokens(text))]
    for sep in seps:
        parts = text.split(sep)
        if len(parts) > 1: break
    else:
        c = max_tokens * 4
        return [Chunk(text[i:i+c].strip(), {}, max_tokens) for i in range(0, len(text), c - overlap * 4)]
    chunks, cur = [], ""
    for part in parts:
        cand = cur + sep + part if cur else part
        if estimate_tokens(cand) > max_tokens and cur:
            chunks.append(Chunk(cur.strip(), {}, estimate_tokens(cur)))
            cur = cur[-(overlap*4):] + sep + part
        else: cur = cand
    if cur.strip(): chunks.append(Chunk(cur.strip(), {}, estimate_tokens(cur)))
    return chunks
```

### Embeddings + Vector Search (pgvector / Pinecone)
```python
import voyageai

async def generate_embeddings(texts: list[str], model: str = "voyage-3") -> list[list[float]]:
    vo = voyageai.AsyncClient(api_key=os.environ["VOYAGE_API_KEY"])
    all_embs = []
    for i in range(0, len(texts), 128):
        result = await vo.embed(texts[i:i+128], model=model, input_type="document")
        all_embs.extend(result.embeddings)
    return all_embs

# pgvector (AWS RDS)
async def setup_pgvector(pool):
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute("""CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY, content TEXT, metadata JSONB DEFAULT '{}',
            embedding vector(1024), created_at TIMESTAMPTZ DEFAULT NOW());""")
        await conn.execute("""CREATE INDEX IF NOT EXISTS idx_chunks_emb ON document_chunks
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);""")

async def vector_search(pool, query_emb: list[float], top_k: int = 5, threshold: float = 0.7) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT content, metadata, 1 - (embedding <=> $1::vector) AS similarity
               FROM document_chunks WHERE 1 - (embedding <=> $1::vector) > $3
               ORDER BY embedding <=> $1::vector LIMIT $2""",
            str(query_emb), top_k, threshold)
        return [{"content": r["content"], "similarity": r["similarity"]} for r in rows]

# Pinecone
from pinecone import Pinecone

def pinecone_search(index_name: str, query_emb: list[float], top_k: int = 5) -> list[dict]:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(index_name)
    results = index.query(vector=query_emb, top_k=top_k, include_metadata=True)
    return [{"content": m.metadata["text"], "score": m.score} for m in results.matches]
```

### RAG Pipeline with Reranking
```python
async def rag_query(question: str, pool, top_k: int = 5, rerank: bool = True) -> str:
    """Embed -> retrieve -> rerank -> generate grounded answer."""
    vo = voyageai.AsyncClient(api_key=os.environ["VOYAGE_API_KEY"])
    q_emb = (await vo.embed([question], model="voyage-3", input_type="query")).embeddings[0]
    candidates = await vector_search(pool, q_emb, top_k=top_k * 3 if rerank else top_k)
    if rerank and candidates:
        reranked = await vo.rerank(query=question, documents=[c["content"] for c in candidates], model="rerank-2", top_k=top_k)
        candidates = [candidates[r.index] for r in reranked.results]
    context = "\n\n---\n\n".join(c["content"] for c in candidates)
    return await generate_response(
        "Answer ONLY from the provided context. If insufficient, say so. Cite passages.",
        f"## Context\n{context}\n\n## Question\n{question}",
    )
```

## Agent Frameworks

### Multi-Agent Orchestration
```python
from enum import Enum

class AgentRole(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"

@dataclass
class AgentConfig:
    role: AgentRole
    system_prompt: str
    model: str = "claude-sonnet-4-5-20250929"
    tools: list[dict] = field(default_factory=list)

class MultiAgentOrchestrator:
    def __init__(self, agents: dict[AgentRole, AgentConfig]):
        self.agents = agents

    async def _run(self, role: AgentRole, text: str) -> str:
        cfg = self.agents[role]
        resp = await client.messages.create(
            model=cfg.model, max_tokens=4096, system=cfg.system_prompt,
            messages=[{"role": "user", "content": text}], tools=cfg.tools or None)
        return resp.content[0].text

    async def orchestrate(self, task: str) -> str:
        plan = await self._run(AgentRole.PLANNER, f"Break into steps:\n{task}")
        research = await self._run(AgentRole.RESEARCHER, f"Research:\n{plan}")
        result = await self._run(AgentRole.EXECUTOR, f"Plan:\n{plan}\n\nResearch:\n{research}")
        review = await self._run(AgentRole.REVIEWER, f"Task: {task}\n\nOutput:\n{result}")
        return f"{result}\n\n---\nReview: {review}"
```

### Memory Patterns
```python
class AgentMemory:
    """Short-term (session) + long-term (vector DB) memory."""
    def __init__(self, pool):
        self.short_term: list[dict] = []
        self.pool = pool

    def remember_short(self, key: str, value: str) -> None:
        self.short_term.append({"key": key, "value": value})

    async def remember_long(self, key: str, value: str, embedding: list[float]) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO agent_memories (key, value, embedding) VALUES ($1,$2,$3::vector)", key, value, str(embedding))

    async def recall(self, query_emb: list[float], top_k: int = 5) -> list[dict]:
        async with self.pool.acquire() as conn:
            return [dict(r) for r in await conn.fetch(
                "SELECT key, value FROM agent_memories ORDER BY embedding <=> $1::vector LIMIT $2", str(query_emb), top_k)]
```

### Planning and Reflection
```python
async def plan_and_execute(task: str, tools: list[dict], max_steps: int = 10) -> str:
    plan = await generate_response("Produce a numbered plan. Output ONLY the plan.", task)
    results = []
    for _ in range(max_steps):
        ctx = f"Task: {task}\nPlan: {plan}\nDone: " + "; ".join(results)
        step = await run_agent_loop(f"{ctx}\nExecute next step.", tools, max_iterations=5)
        results.append(step)
        if "DONE" in (await generate_response("Respond ONLY 'CONTINUE' or 'DONE'.",
            f"Task: {task}\nProgress: {step}", model=LLM_CONFIG["fast"])).upper():
            break
    return await generate_response("Synthesize steps into a final answer.",
        f"Task: {task}\nSteps:\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(results)))
```

## Evaluation and Testing

```python
import pytest
from dataclasses import dataclass

@dataclass
class EvalCase:
    input: str
    expected: str | None = None
    must_contain: list[str] | None = None
    must_not_contain: list[str] | None = None
    max_latency_ms: float | None = None

# TDD: define eval suite BEFORE modifying prompts
SENTIMENT_EVALS = [
    EvalCase(input="BTC just hit a new all-time high!", expected="bullish"),
    EvalCase(input="Market crashed 40% overnight", expected="bearish"),
    EvalCase(input="Trading sideways, low volume", expected="neutral"),
    EvalCase(input="", must_not_contain=["error", "traceback"]),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case", SENTIMENT_EVALS, ids=lambda c: c.input[:30])
async def test_sentiment_eval(case: EvalCase):
    import time; start = time.monotonic()
    result = await classify_sentiment(case.input)
    elapsed = (time.monotonic() - start) * 1000
    if case.expected: assert result.sentiment == case.expected
    if case.must_contain:
        for t in case.must_contain: assert t in result.reasoning
    if case.must_not_contain:
        for t in case.must_not_contain: assert t not in str(result)
    if case.max_latency_ms: assert elapsed < case.max_latency_ms

async def run_eval_suite(fn, cases, threshold=0.9) -> dict:
    """Gate prompt changes in CI on pass rate."""
    passed = 0
    for c in cases:
        try: await fn(c); passed += 1
        except: pass
    rate = passed / len(cases)
    return {"total": len(cases), "passed": passed, "rate": rate, "ok": rate >= threshold}
```

## Guardrails

```python
class OutputGuardrails:
    @staticmethod
    def check_no_hallucinated_data(output: MarketAnalysis, known_price: float) -> bool:
        return all(abs(l - known_price) / known_price <= 0.5
                   for l in output.support_levels + output.resistance_levels)

    @staticmethod
    def check_reasoning_present(output: MarketAnalysis) -> bool:
        return len(output.reasoning) > 20

    @staticmethod
    def check_no_pii(text: str) -> bool:
        import re
        return not any(re.search(p, text) for p in [
            r"\b\d{3}-\d{2}-\d{4}\b", r"\b\d{16}\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"])
```

## Streaming

```python
# Python
async def stream_response(user_message: str, on_text: callable) -> str:
    full = ""
    async with client.messages.stream(
        model="claude-sonnet-4-5-20250929", max_tokens=4096,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full += text; await on_text(text)
    return full
```
```typescript
// TypeScript
async function streamResponse(userMessage: string, onText: (t: string) => void): Promise<string> {
  let full = "";
  const stream = client.messages.stream({
    model: "claude-sonnet-4-5-20250929", max_tokens: 4096,
    messages: [{ role: "user", content: userMessage }],
  });
  for await (const ev of stream) {
    if (ev.type === "content_block_delta" && ev.delta.type === "text_delta") {
      full += ev.delta.text; onText(ev.delta.text);
    }
  }
  return full;
}
```

## Quality Checklist

- [ ] API keys in env vars, never hardcoded (12-Factor III)
- [ ] Model selection via config, not hardcoded in business logic
- [ ] Error handling for all API calls (rate limits, timeouts, server errors)
- [ ] Structured outputs validated against Pydantic / Zod schemas
- [ ] Prompts stored as files or constants (not inline strings)
- [ ] Temperature=0 for deterministic, >0 for creative
- [ ] Token budget managed (counting, truncation, sliding window)
- [ ] Caching: app-level + Anthropic prompt caching
- [ ] Tool use loop has max iteration limit
- [ ] Financial operations validated after LLM generation
- [ ] Eval suite written BEFORE prompt changes (TDD)
- [ ] Streaming for user-facing responses
- [ ] RAG pipeline includes reranking
- [ ] Agent loops include reflection and termination
- [ ] Multi-turn conversations manage context window size

## Anti-Patterns

- Hardcoding API keys or model IDs in source code
- No retry logic (rate limits will hit in production)
- Trusting LLM output for financial calculations without verification
- Inline prompt strings scattered across codebase
- Using the most expensive model for every task
- No token management (sending entire documents as context)
- Synchronous API calls blocking the event loop
- No timeout on API requests
- Manual-only prompt testing (no automated eval suite)
- Ignoring stop_reason (refusals, max_tokens truncation)
- Tool execution without result validation
- Agent loops without iteration limits
- RAG without reranking
- Full conversation history without windowing or compression
- Changing prompts without running evals first
