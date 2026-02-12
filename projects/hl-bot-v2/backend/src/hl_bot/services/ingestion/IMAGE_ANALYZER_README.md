# Image Analyzer for Chart Screenshots

## Overview

The `ImageAnalyzer` service provides AI-powered analysis of trading chart screenshots using Claude Vision. It extracts patterns, price levels, annotations, and trading insights from chart images.

## Features

- **Multi-modal Vision Analysis**: Uses Claude Vision to understand chart images
- **Structured Output**: Returns typed, validated analysis results
- **Pattern Detection**: Identifies candlestick patterns, market structure, and setups
- **Level Extraction**: Detects support, resistance, demand/supply zones
- **Annotation Recognition**: Interprets drawn arrows, boxes, lines, and markings
- **Trading Bias**: Provides actionable long/short/neutral recommendations
- **Caching**: Results are cached to avoid redundant API calls
- **Batch Processing**: Analyze multiple images concurrently
- **Type Safety**: Full type coverage with Pydantic models

## Installation

Required dependencies:
```bash
poetry add anthropic pillow aiofiles pydantic
```

## Usage

### Basic Image Analysis

```python
from pathlib import Path
from hl_bot.services.ingestion.image_analyzer import ImageAnalyzer

# Initialize analyzer
analyzer = ImageAnalyzer()

# Analyze from file path
result = await analyzer.analyze_image(
    Path("./charts/btc_setup.png")
)

# Access structured results
print(f"Trading Bias: {result.analysis.trading_bias}")
print(f"Confidence: {result.analysis.confidence_score}")
print(f"Patterns: {len(result.analysis.patterns)}")

for level in result.analysis.levels:
    print(f"Level: {level.level_type} @ {level.price} ({level.strength})")

for insight in result.analysis.key_insights:
    print(f"• {insight}")
```

### Analyze from Bytes

```python
# From uploaded file
async def analyze_upload(file_bytes: bytes, filename: str):
    analyzer = ImageAnalyzer()
    result = await analyzer.analyze_image(
        image_source=file_bytes,
        filename=filename,
    )
    return result
```

### Analyze from Data URL

```python
# From base64 data URL (useful for web uploads)
data_url = "data:image/png;base64,iVBORw0KGgo..."
result = await analyzer.analyze_image(data_url)
```

### Batch Analysis

```python
# Analyze multiple chart screenshots
image_paths = [
    Path("chart1.png"),
    Path("chart2.png"),
    Path("chart3.png"),
]

results = await analyzer.analyze_batch(
    image_paths,
    max_concurrent=3,  # Analyze 3 at a time
)

for result in results:
    print(f"{result.filename}: {result.analysis.trading_bias}")
```

### Custom Configuration

```python
from hl_bot.services.llm_client import LLMClient

analyzer = ImageAnalyzer(
    llm_client=LLMClient(),  # Use custom LLM client
    cache_dir=Path("./cache"),  # Custom cache location
    model=LLMClient.MODEL_OPUS,  # Use Opus for higher quality
    max_image_size=10 * 1024 * 1024,  # 10MB max
    supported_formats=frozenset(["png", "jpg", "jpeg", "webp"]),
)
```

## API Integration

### FastAPI Endpoint

```python
from fastapi import APIRouter, File, UploadFile
from hl_bot.services.ingestion.image_analyzer import ImageAnalyzer

router = APIRouter()
analyzer = ImageAnalyzer()

@router.post("/analyze-chart")
async def analyze_chart(file: UploadFile = File(...)):
    """Analyze uploaded chart screenshot."""
    content = await file.read()
    
    result = await analyzer.analyze_image(
        image_source=content,
        filename=file.filename,
    )
    
    return {
        "bias": result.analysis.trading_bias,
        "confidence": result.analysis.confidence_score,
        "patterns": [p.pattern_name for p in result.analysis.patterns],
        "levels": [
            {
                "type": l.level_type,
                "price": l.price,
                "strength": l.strength
            }
            for l in result.analysis.levels
        ],
        "insights": result.analysis.key_insights,
    }
```

## Response Structure

### ChartAnalysisResult

```python
class ChartAnalysisResult(BaseModel):
    metadata: ChartMetadata        # Symbol, timeframe, indicators
    trend: TrendAnalysis          # Direction, strength, phase
    patterns: list[DetectedPattern]  # Identified patterns
    levels: list[PriceLevel]      # Support/resistance levels
    annotations: list[ChartAnnotation]  # Drawn markings
    setup_description: str        # Overall setup explanation
    trading_bias: str             # long|short|neutral|wait
    key_insights: list[str]       # Actionable insights
    confidence_score: float       # 0.0-1.0
```

### ChartMetadata

```python
class ChartMetadata(BaseModel):
    symbol: str | None            # e.g., "BTCUSD"
    timeframe: str | None         # e.g., "15m"
    visible_indicators: list[str]  # e.g., ["MA", "RSI"]
    chart_type: str               # candlestick|line|bar
    has_volume: bool
```

### TrendAnalysis

```python
class TrendAnalysis(BaseModel):
    primary_trend: str            # bullish|bearish|neutral|ranging
    trend_strength: str           # weak|moderate|strong
    market_phase: str             # drive|range|liquidity|accumulation
    description: str              # Detailed explanation
```

### DetectedPattern

```python
class DetectedPattern(BaseModel):
    pattern_name: str             # e.g., "LE Candle"
    pattern_category: str         # candle|structure|setup|indicator
    timeframe: str | None
    location: str                 # Where on chart
    confidence: str               # low|medium|high
```

### PriceLevel

```python
class PriceLevel(BaseModel):
    level_type: str               # support|resistance|demand|supply
    price: float | None           # Approximate price if visible
    strength: str                 # weak|moderate|strong|major
    description: str
```

### ChartAnnotation

```python
class ChartAnnotation(BaseModel):
    annotation_type: str          # arrow|box|line|circle|text
    color: str | None
    description: str
    significance: str             # low|medium|high
```

## Caching

Results are automatically cached by image content hash:

```python
# First analysis (calls LLM)
result1 = await analyzer.analyze_image(image_bytes)

# Second analysis (uses cache)
result2 = await analyzer.analyze_image(image_bytes)  # Instant

# Clean up old cache files
removed = await analyzer.cleanup_cache(max_age_days=7)
print(f"Removed {removed} cached files")
```

## Error Handling

```python
from hl_bot.services.ingestion.image_analyzer import ImageAnalyzerError

try:
    result = await analyzer.analyze_image(image_path)
except ImageAnalyzerError as e:
    if "not found" in str(e):
        print("Image file not found")
    elif "too large" in str(e):
        print("Image exceeds size limit")
    elif "Unsupported format" in str(e):
        print("Invalid image format")
    else:
        print(f"Analysis failed: {e}")
```

## Testing

Run the test suite:

```bash
# Unit tests only
pytest tests/unit/test_image_analyzer.py

# Include integration tests (requires API key)
pytest tests/unit/test_image_analyzer.py -m integration

# With coverage
pytest tests/unit/test_image_analyzer.py --cov=hl_bot.services.ingestion.image_analyzer
```

## Performance

- **Single image**: ~3-5 seconds (Claude Vision API latency)
- **Batch (3 concurrent)**: ~5-7 seconds for 10 images
- **Cached results**: < 50ms
- **Memory usage**: ~100MB for analyzer + ~5MB per image in memory

## Limitations

1. **Image Quality**: Works best with clear, high-resolution charts
2. **Annotations**: May not catch very subtle or faint markings
3. **OCR Accuracy**: Price values are approximate if chart axis isn't clear
4. **Context**: Analysis is based solely on the image, no historical data
5. **Rate Limits**: Subject to Anthropic API rate limits

## Best Practices

### Image Preparation

✅ **Good**:
- Clear, high-resolution screenshots (800x600 minimum)
- Candlestick or bar charts (easier to analyze)
- Visible axis labels and timeframe
- High contrast, readable annotations

❌ **Avoid**:
- Very low resolution (< 400px wide)
- Heavy compression artifacts
- Multiple charts in one image
- Charts with heavy overlays obscuring candles

### Usage Patterns

```python
# ✅ Good: Reuse analyzer instance
analyzer = ImageAnalyzer(cache_dir=Path("./cache"))
for image in images:
    await analyzer.analyze_image(image)

# ❌ Avoid: Creating new instance each time
for image in images:
    analyzer = ImageAnalyzer()  # Recreates cache, LLM client
    await analyzer.analyze_image(image)
```

### Concurrent Processing

```python
# ✅ Good: Use batch processing for multiple images
results = await analyzer.analyze_batch(images, max_concurrent=3)

# ❌ Avoid: Sequential processing (slow)
results = []
for image in images:
    result = await analyzer.analyze_image(image)
    results.append(result)
```

## Integration with Strategy Extraction

```python
from hl_bot.services.strategy_extractor import StrategyExtractor

# Analyze chart image
image_result = await image_analyzer.analyze_image(chart_path)

# Convert analysis to text context
context = f"""
Chart Analysis:
- Symbol: {image_result.analysis.metadata.symbol}
- Timeframe: {image_result.analysis.metadata.timeframe}
- Bias: {image_result.analysis.trading_bias}
- Setup: {image_result.analysis.setup_description}

Key Insights:
{chr(10).join(f'- {i}' for i in image_result.analysis.key_insights)}

Patterns Detected:
{chr(10).join(f'- {p.pattern_name} ({p.confidence})' for p in image_result.analysis.patterns)}
"""

# Extract strategies from analysis
extractor = StrategyExtractor()
strategies = await extractor.extract_from_text(
    content=context,
    source_type="image",
    source_id=str(chart_path),
)
```

## Troubleshooting

### "Image too large" Error

```python
# Resize image before analysis
from PIL import Image
from io import BytesIO

img = Image.open("large_chart.png")
img.thumbnail((1920, 1080))  # Max 1920x1080

buffer = BytesIO()
img.save(buffer, format="PNG")
result = await analyzer.analyze_image(buffer.getvalue())
```

### "Unsupported format" Error

```python
# Convert to supported format
from PIL import Image

img = Image.open("chart.bmp")  # BMP not supported
img_rgb = img.convert("RGB")
img_rgb.save("chart.png", "PNG")

result = await analyzer.analyze_image(Path("chart.png"))
```

### Low Confidence Scores

If analysis confidence is consistently low:
1. Ensure image quality is high (800px+ wide)
2. Check that chart is clearly visible
3. Verify annotations are readable
4. Consider using `MODEL_OPUS` for better analysis

```python
analyzer = ImageAnalyzer(model=LLMClient.MODEL_OPUS)
```

## License

MIT License - Part of the HL-Bot-V2 project.

---

**Last Updated:** 2025-02-11  
**Version:** 1.0.0
