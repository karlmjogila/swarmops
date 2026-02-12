"""
Demo script for the LLM strategy extractor.
"""

import asyncio
import json
import logging
from typing import Dict, Any

from ..types import SourceType
from .ingestion_orchestrator import create_ingestion_orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample trading content for demonstration
SAMPLE_STRATEGY_CONTENT = """
# ICT Liquidity Engulf Strategy

## Overview
This strategy focuses on identifying Liquidity Engulf (LE) candles that sweep previous highs/lows to grab liquidity before reversing.

## Entry Rules

### Higher Timeframe Analysis (4H)
1. Identify the overall trend direction
2. Wait for a pullback into a premium/discount zone
3. Look for market structure shift or break of structure

### Lower Timeframe Entry (15M)
1. **LE Candle Requirements:**
   - Body must be at least 70% of total candle range
   - Upper and lower wicks should be less than 30% of range each
   - Candle must close in upper 25% for bullish LE, lower 25% for bearish LE
   - Volume should be 1.5x average volume

2. **Confluence Factors:**
   - LE candle sweeps previous high/low
   - Rejection from key level (support/resistance)
   - Time of day: London or New York session
   - No high-impact news within 30 minutes

## Risk Management
- **Stop Loss:** Place below/above the LE candle low/high
- **Take Profit 1:** 1R (1:1 risk-reward)
- **Take Profit 2:** 2R (1:2 risk-reward) 
- **Position Size:** Risk 2% of account per trade
- **Max Concurrent:** 3 positions maximum

## Example Setup
Entry: 1.2500 (bullish LE candle)
Stop Loss: 1.2480 (20 pips risk)
TP1: 1.2520 (20 pips = 1R)
TP2: 1.2540 (40 pips = 2R)

## Market Conditions
- **Best in:** Trending markets during drive phase
- **Avoid during:** Major news events, low liquidity hours, ranging markets
"""


SAMPLE_PATTERN_CONTENT = """
# Steeper Wick Rejection Pattern

## What is a Steeper Wick?
A steeper wick forms when price aggressively rejects from a key level, creating a long wick (shadow) relative to the body.

## Identification Criteria
1. **Wick-to-Total Ratio:** Rejection wick must be at least 60% of total candle range
2. **Body Position:** Candle body should be in lower 40% for bullish, upper 40% for bearish
3. **Volume:** Higher than average volume on the rejection candle
4. **Level Interaction:** Must occur at significant support/resistance level

## Entry Method
- **Entry:** Open of next candle after steeper wick confirmation
- **Confirmation:** Next candle should not break the rejection level
- **Timeframe:** Works best on 15M and 1H charts

## Risk Parameters
- **Stop Loss:** 10 pips beyond the rejection wick extreme
- **Target:** Previous swing high/low or next structure level
- **Risk:** 1.5% per trade
- **Max Drawdown:** Exit if 3 consecutive losses

## Best Market Conditions
- Strong trending markets
- At key structure levels
- During high volume sessions (London/NY overlap)
"""


async def demo_strategy_extraction():
    """Demonstrate strategy extraction from sample content."""
    logger.info("Starting LLM Strategy Extractor Demo")
    
    try:
        # Create ingestion orchestrator
        orchestrator = create_ingestion_orchestrator()
        
        logger.info("=== Extracting from ICT Strategy Content ===")
        
        # Process ICT strategy content
        response1 = await orchestrator.ingest_content(
            content=SAMPLE_STRATEGY_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="demo_ict_strategy.md",
            tags=["ict", "liquidity", "demo"]
        )
        
        print(f"Task ID: {response1.task_id}")
        print(f"Status: {response1.status}")
        print(f"Message: {response1.message}")
        print(f"Strategies Created: {len(response1.strategy_rules_created)}")
        print()
        
        logger.info("=== Extracting from Pattern Content ===")
        
        # Process pattern content
        response2 = await orchestrator.ingest_content(
            content=SAMPLE_PATTERN_CONTENT,
            source_type=SourceType.MANUAL,
            source_ref="demo_steeper_wick.md",
            tags=["pattern", "wick", "demo"]
        )
        
        print(f"Task ID: {response2.task_id}")
        print(f"Status: {response2.status}")
        print(f"Message: {response2.message}")
        print(f"Strategies Created: {len(response2.strategy_rules_created)}")
        print()
        
        # Show processing stats
        stats = orchestrator.get_processing_stats()
        logger.info("=== Processing Statistics ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        logger.info("Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


async def demo_content_analysis():
    """Demonstrate content analysis capabilities."""
    logger.info("=== Content Analysis Demo ===")
    
    from .content_analyzer import ContentAnalyzer
    
    analyzer = ContentAnalyzer()
    
    # Analyze different types of content
    contents = [
        (SAMPLE_STRATEGY_CONTENT, "ICT Strategy"),
        (SAMPLE_PATTERN_CONTENT, "Pattern Guide"),
        ("Just some general trading advice about being disciplined.", "General Advice"),
        ("Buy low sell high. Good luck!", "Poor Content")
    ]
    
    for content, label in contents:
        print(f"\n--- Analysis for: {label} ---")
        
        analysis = analyzer.analyze_content(content, SourceType.MANUAL)
        
        print(f"Content Type: {analysis['content_type']}")
        print(f"Quality: {analysis['quality']}")
        print(f"Extraction Confidence: {analysis['extraction_confidence']:.2f}")
        print(f"Word Count: {analysis['metrics']['word_count']}")
        print(f"Topics: {', '.join(analysis['topics'])}")
        print(f"Should Process: {analyzer.should_process_content(analysis)}")


async def demo_batch_processing():
    """Demonstrate batch processing of multiple sources."""
    logger.info("=== Batch Processing Demo ===")
    
    orchestrator = create_ingestion_orchestrator()
    
    # Simulate multiple sources
    sources = [
        {
            "type": "manual",
            "content": SAMPLE_STRATEGY_CONTENT,
            "ref": "ict_strategy.md",
            "tags": ["ict", "batch"]
        },
        {
            "type": "manual", 
            "content": SAMPLE_PATTERN_CONTENT,
            "ref": "pattern_guide.md",
            "tags": ["pattern", "batch"]
        },
        {
            "type": "manual",
            "content": "Short content that might not extract well.",
            "ref": "short_content.md",
            "tags": ["test", "batch"]
        }
    ]
    
    # Process batch
    responses = await orchestrator.batch_ingest(sources, max_concurrent=2)
    
    print(f"\nBatch Processing Results:")
    print(f"Total Sources: {len(sources)}")
    
    for i, response in enumerate(responses):
        print(f"\nSource {i+1}:")
        print(f"  Status: {response.status}")
        print(f"  Strategies: {len(response.strategy_rules_created)}")
        print(f"  Message: {response.message}")


if __name__ == "__main__":
    async def main():
        """Run all demos."""
        try:
            await demo_content_analysis()
            print("\n" + "="*60 + "\n")
            await demo_strategy_extraction()
            print("\n" + "="*60 + "\n")
            await demo_batch_processing()
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Note: This would need proper async setup to run
    print("LLM Strategy Extractor Demo")
    print("To run this demo, you would need:")
    print("1. Valid Anthropic API key in environment")
    print("2. Proper async execution context")
    print("3. Full project dependencies installed")
    print("\nExample usage:")
    print("asyncio.run(main())")