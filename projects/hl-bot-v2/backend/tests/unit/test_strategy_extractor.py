"""Unit tests for strategy extractor."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hl_bot.services.llm_client import LLMClient
from hl_bot.services.strategy_extractor import PromptManager, StrategyExtractor
from hl_bot.types import StrategyRule


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock(spec=LLMClient)
    client.generate = AsyncMock()
    client.analyze_image = AsyncMock()
    client.estimate_tokens = MagicMock(return_value=1000)
    client.truncate_to_fit = MagicMock(side_effect=lambda text, *args, **kwargs: text)
    return client


@pytest.fixture
def valid_strategy_json():
    """Sample valid strategy JSON response."""
    return json.dumps(
        [
            {
                "name": "LE Candle at Support",
                "description": "Enter long when LE candle forms at support zone",
                "timeframes": ["5m", "15m"],
                "market_phase": "drive",
                "entry_conditions": [
                    {
                        "field": "pattern_type",
                        "operator": "eq",
                        "value": "le_candle",
                        "description": "Look for LE candle pattern",
                    },
                    {
                        "field": "zone_type",
                        "operator": "in",
                        "value": ["support", "demand"],
                        "description": "Price at support or demand zone",
                    },
                    {
                        "field": "confluence_score",
                        "operator": "gte",
                        "value": 70,
                        "description": "High confluence score",
                    },
                ],
                "exit_rules": {
                    "tp1_percent": 1.0,
                    "tp1_position_percent": 0.5,
                    "tp2_percent": 2.0,
                    "tp3_percent": 3.0,
                    "move_to_breakeven_at": 1.0,
                    "trailing_stop": False,
                    "trailing_stop_trigger": None,
                },
                "risk_params": {
                    "risk_percent": 0.01,
                    "max_positions": 3,
                    "max_correlation": 0.7,
                    "max_daily_loss": 0.05,
                },
            }
        ]
    )


@pytest.mark.asyncio
async def test_extract_from_text_success(mock_llm_client, valid_strategy_json):
    """Test successful strategy extraction from text."""
    mock_llm_client.generate.return_value = valid_strategy_json

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_text(
        content="Test trading content with strategy description",
        source_type="youtube",
        source_id="https://youtube.com/watch?v=test",
    )

    assert len(strategies) == 1
    strategy = strategies[0]

    assert isinstance(strategy.rule, StrategyRule)
    assert strategy.rule.name == "LE Candle at Support"
    assert len(strategy.rule.timeframes) == 2
    assert len(strategy.rule.entry_conditions) == 3
    assert strategy.confidence > 0.5

    # Verify LLM was called
    mock_llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_extract_from_text_empty_response(mock_llm_client):
    """Test handling of empty strategy response."""
    mock_llm_client.generate.return_value = "[]"

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_text(
        content="Content with no clear strategies",
        source_type="pdf",
        source_id="document.pdf",
    )

    assert len(strategies) == 0


@pytest.mark.asyncio
async def test_extract_from_text_invalid_json(mock_llm_client):
    """Test handling of invalid JSON response."""
    mock_llm_client.generate.return_value = "Not valid JSON"

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    with pytest.raises(ValueError, match="Invalid JSON response"):
        await extractor.extract_from_text(
            content="Test content",
            source_type="youtube",
            source_id="test",
        )


@pytest.mark.asyncio
async def test_extract_from_text_markdown_wrapped(mock_llm_client, valid_strategy_json):
    """Test handling of JSON wrapped in markdown code blocks."""
    mock_llm_client.generate.return_value = f"```json\n{valid_strategy_json}\n```"

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_text(
        content="Test content",
        source_type="youtube",
        source_id="test",
    )

    assert len(strategies) == 1


@pytest.mark.asyncio
async def test_extract_from_text_partial_invalid(mock_llm_client):
    """Test handling of partially invalid strategies."""
    response = json.dumps(
        [
            {
                "name": "Valid Strategy",
                "description": "A valid strategy",
                "timeframes": ["5m"],
                "market_phase": "range",
                "entry_conditions": [
                    {
                        "field": "pattern_type",
                        "operator": "eq",
                        "value": "le_candle",
                        "description": "LE candle",
                    }
                ],
                "exit_rules": {
                    "tp1_percent": 1.0,
                    "tp1_position_percent": 0.5,
                    "tp2_percent": 2.0,
                    "move_to_breakeven_at": 1.0,
                },
                "risk_params": {
                    "risk_percent": 0.01,
                    "max_positions": 3,
                    "max_correlation": 0.7,
                    "max_daily_loss": 0.05,
                },
            },
            {
                "name": "Invalid Strategy",
                # Missing required fields
            },
        ]
    )

    mock_llm_client.generate.return_value = response

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_text(
        content="Test content",
        source_type="youtube",
        source_id="test",
    )

    # Should extract only the valid one
    assert len(strategies) == 1
    assert strategies[0].rule.name == "Valid Strategy"


@pytest.mark.asyncio
async def test_extract_from_images(mock_llm_client, valid_strategy_json):
    """Test strategy extraction from images."""
    # Mock image analysis
    mock_llm_client.analyze_image.return_value = (
        "Chart shows LE candle at support level with bullish structure"
    )

    # Mock final extraction
    mock_llm_client.generate.return_value = valid_strategy_json

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_images(
        image_urls=["https://example.com/chart1.png", "https://example.com/chart2.png"],
        context_text="Additional context from video transcript",
        source_type="youtube",
        source_id="https://youtube.com/watch?v=test",
    )

    assert len(strategies) == 1

    # Verify image analysis was called for each image
    assert mock_llm_client.analyze_image.call_count == 2

    # Verify final extraction was called with combined content
    mock_llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_extract_from_images_analysis_failure(mock_llm_client, valid_strategy_json):
    """Test handling of image analysis failures."""
    # First image fails, second succeeds
    mock_llm_client.analyze_image.side_effect = [
        Exception("Analysis failed"),
        "Chart shows valid setup",
    ]

    mock_llm_client.generate.return_value = valid_strategy_json

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    strategies = await extractor.extract_from_images(
        image_urls=["https://example.com/chart1.png", "https://example.com/chart2.png"],
        source_type="youtube",
        source_id="test",
    )

    # Should still succeed with partial images
    assert len(strategies) == 1


@pytest.mark.asyncio
async def test_extract_long_content_truncation(mock_llm_client, valid_strategy_json):
    """Test that long content is truncated."""
    mock_llm_client.estimate_tokens.return_value = 100000  # Very long
    mock_llm_client.truncate_to_fit.return_value = "Truncated content"
    mock_llm_client.generate.return_value = valid_strategy_json

    extractor = StrategyExtractor(llm_client=mock_llm_client)

    long_content = "a" * 1000000  # Very long content

    strategies = await extractor.extract_from_text(
        content=long_content,
        source_type="pdf",
        source_id="long_document.pdf",
    )

    # Should call truncation
    mock_llm_client.truncate_to_fit.assert_called_once()

    # Should still extract strategies
    assert len(strategies) == 1


def test_confidence_calculation():
    """Test confidence score calculation."""
    from hl_bot.services.strategy_extractor import StrategyExtractorOutput

    # High quality strategy
    high_quality = StrategyExtractorOutput(
        name="Detailed Strategy Name",
        description="Very detailed description of the trading strategy with clear explanation",
        timeframes=["5m", "15m"],
        market_phase="drive",
        entry_conditions=[
            {
                "field": "pattern_type",
                "operator": "eq",
                "value": "le_candle",
                "description": "LE candle",
            },
            {
                "field": "zone_type",
                "operator": "eq",
                "value": "support",
                "description": "At support",
            },
            {
                "field": "confluence_score",
                "operator": "gte",
                "value": 70,
                "description": "High confluence",
            },
        ],
        exit_rules={
            "tp1_percent": 1.0,
            "tp1_position_percent": 0.5,
            "tp2_percent": 2.0,
            "move_to_breakeven_at": 1.0,
        },
        risk_params={
            "risk_percent": 0.01,
            "max_positions": 3,
            "max_daily_loss": 0.05,
        },
    )

    extractor = StrategyExtractor()
    confidence = extractor._calculate_confidence(high_quality)

    assert confidence > 0.8  # Should be high quality

    # Low quality strategy
    low_quality = StrategyExtractorOutput(
        name="Test",
        description="Short",
        timeframes=["5m"],
        market_phase="unknown",
        entry_conditions=[
            {
                "field": "test",
                "operator": "eq",
                "value": "test",
                "description": "test",
            }
        ],
        exit_rules={"tp1_percent": 1.0},
        risk_params={"risk_percent": 0.01},
    )

    confidence = extractor._calculate_confidence(low_quality)

    assert confidence < 0.5  # Should be low quality


def test_prompt_manager_default_prompts():
    """Test prompt manager with default inline prompts."""
    manager = PromptManager()

    # Should load default prompts
    extract_prompt = manager.get("extract_strategy", content="test content")
    assert "test content" in extract_prompt
    assert "trading strategy" in extract_prompt.lower()

    chart_prompt = manager.get("analyze_chart_image")
    assert "chart" in chart_prompt.lower()


def test_prompt_manager_template_substitution():
    """Test template variable substitution."""
    manager = PromptManager()

    prompt = manager.get("extract_strategy", content="My custom content here")
    assert "My custom content here" in prompt


def test_convert_to_strategy_rule():
    """Test conversion from intermediate output to StrategyRule."""
    from hl_bot.services.strategy_extractor import StrategyExtractorOutput

    intermediate = StrategyExtractorOutput(
        name="Test Strategy",
        description="Test description",
        timeframes=["5m", "15m"],
        market_phase="drive",
        entry_conditions=[
            {
                "field": "pattern_type",
                "operator": "eq",
                "value": "le_candle",
                "description": "LE candle pattern",
            }
        ],
        exit_rules={
            "tp1_percent": 1.0,
            "tp1_position_percent": 0.5,
            "tp2_percent": 2.0,
            "move_to_breakeven_at": 1.0,
        },
        risk_params={
            "risk_percent": 0.01,
            "max_positions": 3,
            "max_correlation": 0.7,
            "max_daily_loss": 0.05,
        },
    )

    extractor = StrategyExtractor()
    strategy_rule = extractor._convert_to_strategy_rule(
        intermediate=intermediate,
        source_type="youtube",
        source_id="https://youtube.com/test",
    )

    assert isinstance(strategy_rule, StrategyRule)
    assert strategy_rule.name == "Test Strategy"
    assert len(strategy_rule.timeframes) == 2
    assert len(strategy_rule.entry_conditions) == 1
    assert strategy_rule.source.source_type == "youtube"
