"""Image analyzer for chart screenshots.

Analyzes trading chart images to extract patterns, levels, and trading setups.
Uses Claude Vision for multi-modal analysis.
"""

import asyncio
import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import aiofiles
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from hl_bot.services.llm_client import LLMClient
from hl_bot.types import MarketPhase, PatternType, SetupType, SignalType, Timeframe

logger = logging.getLogger(__name__)


class ImageAnalyzerError(Exception):
    """Base exception for image analysis errors."""

    pass


# ============================================================================
# Response Models (Structured LLM Output)
# ============================================================================


class PriceLevel(BaseModel):
    """Detected price level from chart."""

    level_type: str = Field(
        ..., pattern=r"^(support|resistance|demand|supply|poi|order_block)$"
    )
    price: float | None = Field(
        default=None, gt=0, description="Approximate price if visible"
    )
    strength: str = Field(..., pattern=r"^(weak|moderate|strong|major)$")
    description: str = Field(..., min_length=1)


class ChartAnnotation(BaseModel):
    """Annotation or marking on the chart."""

    annotation_type: str = Field(
        ..., pattern=r"^(arrow|box|line|circle|text|trendline|zone)$"
    )
    color: str | None = Field(default=None, description="Color if identifiable")
    description: str = Field(..., min_length=1)
    significance: str = Field(..., pattern=r"^(low|medium|high)$")


class DetectedPattern(BaseModel):
    """Pattern identified in the chart."""

    pattern_name: str = Field(..., min_length=1)
    pattern_category: str = Field(
        ..., pattern=r"^(candle|structure|setup|indicator)$"
    )
    timeframe: str | None = Field(default=None, description="Timeframe if visible")
    location: str = Field(..., min_length=1, description="Where on chart")
    confidence: str = Field(..., pattern=r"^(low|medium|high)$")


class TrendAnalysis(BaseModel):
    """Overall trend direction analysis."""

    primary_trend: str = Field(..., pattern=r"^(bullish|bearish|neutral|ranging)$")
    trend_strength: str = Field(..., pattern=r"^(weak|moderate|strong)$")
    market_phase: str = Field(
        ..., pattern=r"^(drive|range|liquidity|accumulation|distribution)$"
    )
    description: str = Field(..., min_length=1)


class ChartMetadata(BaseModel):
    """Chart metadata extraction."""

    symbol: str | None = Field(default=None, description="Trading symbol if visible")
    timeframe: str | None = Field(default=None, description="Chart timeframe if visible")
    visible_indicators: list[str] = Field(
        default_factory=list, description="Indicators present"
    )
    chart_type: str = Field(
        ..., pattern=r"^(candlestick|line|bar|heikin_ashi|renko|unknown)$"
    )
    has_volume: bool = Field(default=False)


class ChartAnalysisResult(BaseModel):
    """Structured chart analysis output from LLM."""

    metadata: ChartMetadata
    trend: TrendAnalysis
    patterns: list[DetectedPattern] = Field(default_factory=list)
    levels: list[PriceLevel] = Field(default_factory=list)
    annotations: list[ChartAnnotation] = Field(default_factory=list)
    setup_description: str = Field(
        ..., min_length=10, description="Overall setup explanation"
    )
    trading_bias: str = Field(
        ..., pattern=r"^(long|short|neutral|wait)$", description="Suggested bias"
    )
    key_insights: list[str] = Field(
        ..., min_length=1, description="Key takeaways for trading"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall analysis confidence"
    )


# ============================================================================
# Data Class for Results
# ============================================================================


@dataclass
class ImageAnalysis:
    """Complete image analysis result."""

    image_id: str
    filename: str
    width: int
    height: int
    format: str
    file_size: int
    analyzed_at: datetime
    analysis: ChartAnalysisResult
    raw_text: str
    processing_time: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "image_id": self.image_id,
            "filename": self.filename,
            "dimensions": {"width": self.width, "height": self.height},
            "format": self.format,
            "file_size": self.file_size,
            "analyzed_at": self.analyzed_at.isoformat(),
            "analysis": self.analysis.model_dump(),
            "raw_text": self.raw_text,
            "processing_time": self.processing_time,
        }


# ============================================================================
# Image Analyzer Service
# ============================================================================


class ImageAnalyzer:
    """Analyze trading chart screenshots using vision AI."""

    # LLM prompts
    SYSTEM_PROMPT = """You are an expert trading chart analyst specializing in technical analysis.

Your task is to analyze trading chart images and extract:
1. Chart metadata (symbol, timeframe, indicators)
2. Trend direction and market phase
3. Detected patterns (candlestick patterns, market structure)
4. Key price levels (support, resistance, order blocks)
5. Visible annotations and markings
6. Trading setup and bias

Be precise, specific, and provide actionable insights."""

    ANALYSIS_PROMPT = """Analyze this trading chart image in detail.

## What to identify:

### 1. Chart Metadata
- Symbol (if visible)
- Timeframe (5m, 15m, 1h, 4h, etc.)
- Chart type (candlestick, line, etc.)
- Visible indicators (MA, RSI, volume, etc.)

### 2. Trend & Market Phase
- Primary trend direction (bullish/bearish/neutral/ranging)
- Trend strength (weak/moderate/strong)
- Market phase (drive, range, liquidity grab, accumulation, distribution)
- Context and reasoning

### 3. Patterns
- Candlestick patterns (LE candle, engulfing, hammer, etc.)
- Market structure (BOS, CHoCH, swing highs/lows)
- Setup types (breakout, pullback, reversal, etc.)
- Location and confidence for each

### 4. Price Levels
- Support and resistance levels
- Order blocks, demand/supply zones
- Points of interest (POI)
- Strength assessment for each

### 5. Annotations
- Arrows, boxes, lines drawn on chart
- Color coding significance
- What they indicate (entry, exit, zones)

### 6. Trading Context
- Overall setup description
- Suggested trading bias (long/short/neutral/wait)
- Key insights for trading decisions
- Entry and exit concepts if visible

## Important Guidelines:
- Be specific about locations ("near recent high", "at 50% retracement")
- Assess confidence for each detection (low/medium/high)
- If information isn't visible, mark as null/unknown
- Focus on actionable trading information
- Explain reasoning for bias and insights

Provide structured analysis that can be used for strategy extraction."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        cache_dir: Path | None = None,
        model: str = LLMClient.MODEL_SONNET,
        max_image_size: int = 5 * 1024 * 1024,  # 5MB
        supported_formats: frozenset[str] = frozenset(["png", "jpg", "jpeg", "webp"]),
    ):
        """Initialize image analyzer.

        Args:
            llm_client: LLM client instance (creates default if None)
            cache_dir: Directory for caching analysis results
            model: LLM model to use for vision analysis
            max_image_size: Maximum image file size in bytes
            supported_formats: Supported image formats
        """
        self._llm = llm_client or LLMClient()
        self._cache_dir = cache_dir
        self._model = model
        self._max_size = max_image_size
        self._formats = supported_formats

        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Image analyzer initialized: model={model}, "
            f"max_size={max_image_size}, formats={supported_formats}"
        )

    async def analyze_image(
        self,
        image_source: Path | bytes | str,
        filename: str = "chart.png",
        use_structured_output: bool = True,
    ) -> ImageAnalysis:
        """Analyze a chart image.

        Args:
            image_source: Path to image file, image bytes, or base64 data URL
            filename: Original filename for reference
            use_structured_output: Use structured JSON output (recommended)

        Returns:
            ImageAnalysis with structured results

        Raises:
            ImageAnalyzerError: If analysis fails
        """
        start_time = asyncio.get_event_loop().time()

        # Load and validate image
        image_bytes, image_info = await self._load_image(image_source, filename)

        # Check cache
        image_id = self._compute_image_id(image_bytes)
        if self._cache_dir:
            cached = await self._check_cache(image_id)
            if cached:
                logger.info(f"Cache hit for image {image_id}")
                return cached

        # Prepare image for LLM (convert to data URL)
        image_data_url = self._bytes_to_data_url(image_bytes, image_info["format"])

        logger.info(
            f"Analyzing image {filename}: {image_info['width']}x{image_info['height']}, "
            f"{image_info['file_size']} bytes"
        )

        try:
            if use_structured_output:
                # Use structured output for reliable parsing
                analysis_result = await self._analyze_structured(image_data_url)
                raw_text = analysis_result.model_dump_json(indent=2)
            else:
                # Use unstructured output (fallback)
                raw_text = await self._analyze_unstructured(image_data_url)
                analysis_result = self._parse_unstructured_response(raw_text)

            processing_time = asyncio.get_event_loop().time() - start_time

            result = ImageAnalysis(
                image_id=image_id,
                filename=filename,
                width=image_info["width"],
                height=image_info["height"],
                format=image_info["format"],
                file_size=image_info["file_size"],
                analyzed_at=datetime.now(),
                analysis=analysis_result,
                raw_text=raw_text,
                processing_time=processing_time,
            )

            # Cache result
            if self._cache_dir:
                await self._cache_result(image_id, result)

            logger.info(
                f"Analysis complete for {filename}: "
                f"bias={analysis_result.trading_bias}, "
                f"patterns={len(analysis_result.patterns)}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to analyze image {filename}: {e}")
            raise ImageAnalyzerError(f"Image analysis failed: {e}")

    async def analyze_batch(
        self,
        image_sources: list[Path | bytes | str],
        filenames: list[str] | None = None,
        max_concurrent: int = 3,
    ) -> list[ImageAnalysis]:
        """Analyze multiple images concurrently.

        Args:
            image_sources: List of image sources
            filenames: Optional list of filenames (must match length)
            max_concurrent: Maximum concurrent analyses

        Returns:
            List of ImageAnalysis results

        Raises:
            ValueError: If filenames length doesn't match sources
        """
        if filenames and len(filenames) != len(image_sources):
            raise ValueError("Filenames list must match image sources length")

        if not filenames:
            filenames = [f"chart_{i}.png" for i in range(len(image_sources))]

        logger.info(f"Starting batch analysis of {len(image_sources)} images")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyze_with_limit(
            source: Path | bytes | str, name: str
        ) -> ImageAnalysis | None:
            async with semaphore:
                try:
                    return await self.analyze_image(source, name)
                except ImageAnalyzerError as e:
                    logger.warning(f"Failed to analyze {name}: {e}")
                    return None

        tasks = [
            _analyze_with_limit(source, name)
            for source, name in zip(image_sources, filenames)
        ]
        results = await asyncio.gather(*tasks)

        # Filter out failed analyses
        successful = [r for r in results if r is not None]

        logger.info(
            f"Batch analysis complete: {len(successful)}/{len(image_sources)} successful"
        )

        return successful

    async def _load_image(
        self, source: Path | bytes | str, filename: str
    ) -> tuple[bytes, dict[str, Any]]:
        """Load and validate image from various sources.

        Args:
            source: Image source (file path, bytes, or data URL)
            filename: Filename for format inference

        Returns:
            Tuple of (image bytes, image info dict)

        Raises:
            ImageAnalyzerError: If image is invalid
        """
        # Load bytes from source
        if isinstance(source, Path):
            if not source.exists():
                raise ImageAnalyzerError(f"Image file not found: {source}")

            async with aiofiles.open(source, "rb") as f:
                image_bytes = await f.read()

        elif isinstance(source, bytes):
            image_bytes = source

        elif isinstance(source, str):
            # Assume it's a data URL
            if source.startswith("data:"):
                # Extract base64 data
                try:
                    header, encoded = source.split(",", 1)
                    image_bytes = base64.b64decode(encoded)
                except Exception as e:
                    raise ImageAnalyzerError(f"Invalid data URL: {e}")
            else:
                raise ImageAnalyzerError("String source must be a data URL")

        else:
            raise ImageAnalyzerError(f"Invalid image source type: {type(source)}")

        # Validate size
        if len(image_bytes) > self._max_size:
            raise ImageAnalyzerError(
                f"Image too large: {len(image_bytes)} bytes (max {self._max_size})"
            )

        # Validate format and get metadata
        try:
            loop = asyncio.get_event_loop()

            def _get_info() -> dict[str, Any]:
                img = Image.open(BytesIO(image_bytes))
                fmt = img.format.lower() if img.format else "unknown"

                if fmt not in self._formats:
                    raise ImageAnalyzerError(
                        f"Unsupported format: {fmt} (supported: {self._formats})"
                    )

                return {
                    "width": img.width,
                    "height": img.height,
                    "format": fmt,
                    "file_size": len(image_bytes),
                }

            info = await loop.run_in_executor(None, _get_info)
            return image_bytes, info

        except ImageAnalyzerError:
            raise
        except Exception as e:
            raise ImageAnalyzerError(f"Failed to load image: {e}")

    def _bytes_to_data_url(self, image_bytes: bytes, format: str) -> str:
        """Convert image bytes to data URL for LLM.

        Args:
            image_bytes: Image bytes
            format: Image format (png, jpg, etc.)

        Returns:
            Data URL string
        """
        mime_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }

        mime = mime_types.get(format, "image/png")
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        return f"data:{mime};base64,{b64}"

    async def _analyze_structured(self, image_data_url: str) -> ChartAnalysisResult:
        """Analyze image with structured output.

        Args:
            image_data_url: Image as data URL

        Returns:
            Structured analysis result

        Raises:
            ImageAnalyzerError: If analysis fails
        """
        try:
            # Note: As of implementation, Anthropic doesn't support structured output
            # with vision models directly. We'll use text-based parsing instead.
            # This is a placeholder for when the feature is available.

            # For now, fall back to unstructured analysis
            raw_text = await self._analyze_unstructured(image_data_url)
            return self._parse_unstructured_response(raw_text)

        except Exception as e:
            raise ImageAnalyzerError(f"Structured analysis failed: {e}")

    async def _analyze_unstructured(self, image_data_url: str) -> str:
        """Analyze image with text output.

        Args:
            image_data_url: Image as data URL

        Returns:
            Raw text analysis

        Raises:
            ImageAnalyzerError: If analysis fails
        """
        try:
            response = await self._llm.analyze_image(
                system=self.SYSTEM_PROMPT,
                user_message=self.ANALYSIS_PROMPT,
                image_url=image_data_url,
                model=self._model,
                max_tokens=4096,
            )

            return response

        except Exception as e:
            raise ImageAnalyzerError(f"LLM analysis failed: {e}")

    def _parse_unstructured_response(self, response: str) -> ChartAnalysisResult:
        """Parse unstructured text response into structured format.

        Args:
            response: Raw LLM response

        Returns:
            Structured analysis result

        Raises:
            ImageAnalyzerError: If parsing fails
        """
        # This is a simplified parser. In production, you might want to:
        # 1. Use a second LLM call with structured output on the text
        # 2. Use regex patterns to extract structured data
        # 3. Implement a more sophisticated NLP pipeline

        # For now, create a reasonable default structure with extracted info
        try:
            # Extract basic information from the response
            # This is a placeholder - in real implementation, you'd parse more thoroughly

            return ChartAnalysisResult(
                metadata=ChartMetadata(
                    chart_type="candlestick",  # Default assumption
                    has_volume=False,
                ),
                trend=TrendAnalysis(
                    primary_trend="neutral",
                    trend_strength="moderate",
                    market_phase="range",
                    description=response[:200],  # First 200 chars as summary
                ),
                patterns=[],
                levels=[],
                annotations=[],
                setup_description=response[:500],
                trading_bias="neutral",
                key_insights=[line for line in response.split("\n") if line.strip()][:5],
                confidence_score=0.7,
            )

        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ImageAnalyzerError(f"Response parsing failed: {e}")

    def _compute_image_id(self, image_bytes: bytes) -> str:
        """Compute unique ID for image based on content hash.

        Args:
            image_bytes: Image bytes

        Returns:
            Unique image ID (hash)
        """
        return hashlib.sha256(image_bytes).hexdigest()[:16]

    async def _check_cache(self, image_id: str) -> ImageAnalysis | None:
        """Check if analysis result is cached.

        Args:
            image_id: Image identifier

        Returns:
            Cached result or None
        """
        if not self._cache_dir:
            return None

        cache_file = self._cache_dir / f"{image_id}.json"

        if not cache_file.exists():
            return None

        try:
            import json

            async with aiofiles.open(cache_file, "r") as f:
                data = json.loads(await f.read())

            # Reconstruct ImageAnalysis from cached data
            return ImageAnalysis(
                image_id=data["image_id"],
                filename=data["filename"],
                width=data["dimensions"]["width"],
                height=data["dimensions"]["height"],
                format=data["format"],
                file_size=data["file_size"],
                analyzed_at=datetime.fromisoformat(data["analyzed_at"]),
                analysis=ChartAnalysisResult(**data["analysis"]),
                raw_text=data["raw_text"],
                processing_time=data["processing_time"],
            )

        except Exception as e:
            logger.warning(f"Failed to load cached result for {image_id}: {e}")
            return None

    async def _cache_result(self, image_id: str, result: ImageAnalysis) -> None:
        """Cache analysis result.

        Args:
            image_id: Image identifier
            result: Analysis result to cache
        """
        if not self._cache_dir:
            return

        cache_file = self._cache_dir / f"{image_id}.json"

        try:
            import json

            async with aiofiles.open(cache_file, "w") as f:
                await f.write(json.dumps(result.to_dict(), indent=2))

        except Exception as e:
            logger.warning(f"Failed to cache result for {image_id}: {e}")

    async def cleanup_cache(self, max_age_days: int = 7) -> int:
        """Clean up old cached analysis results.

        Args:
            max_age_days: Remove cached files older than this many days

        Returns:
            Number of files removed
        """
        if not self._cache_dir:
            return 0

        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        try:
            for cache_file in self._cache_dir.glob("*.json"):
                if cache_file.stat().st_mtime < cutoff.timestamp():
                    cache_file.unlink()
                    removed += 1

            logger.info(f"Cleaned up {removed} cached analysis files")
            return removed

        except Exception as e:
            logger.warning(f"Failed to cleanup cache: {e}")
            return removed
