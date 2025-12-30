"""AI service for document analysis using Claude and GPT-4

Provides:
- Document summarization and classification using Claude 3.5 Sonnet
- Structured entity extraction using GPT-4
- Cost tracking and budget management
- Retry logic with exponential backoff
"""
import asyncio
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
import json

try:
    from anthropic import Anthropic, APIError as AnthropicAPIError, RateLimitError as AnthropicRateLimitError
except ImportError:
    Anthropic = None
    AnthropicAPIError = Exception
    AnthropicRateLimitError = Exception

try:
    from openai import OpenAI, APIError as OpenAIAPIError, RateLimitError as OpenAIRateLimitError
except ImportError:
    OpenAI = None
    OpenAIAPIError = Exception
    OpenAIRateLimitError = Exception

from app.config import get_settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered document analysis"""

    # Model configurations
    CLAUDE_MODEL = "claude-3-5-haiku-20241022"  # Claude 3.5 Haiku (fast, cheap, available on free tier)
    GPT4_MODEL = "gpt-4-turbo-preview"

    # Pricing (per 1M tokens) - Claude 3.5 Haiku pricing
    CLAUDE_INPUT_PRICE = 0.80  # $0.80 per 1M input tokens
    CLAUDE_OUTPUT_PRICE = 4.00  # $4 per 1M output tokens
    GPT4_INPUT_PRICE = 10.00  # $10 per 1M input tokens
    GPT4_OUTPUT_PRICE = 30.00  # $30 per 1M output tokens

    def __init__(self):
        """Initialize AI service with API clients"""
        settings = get_settings()

        # Initialize Anthropic client (REQUIRED)
        if not Anthropic:
            raise ImportError("anthropic library is required. Install with: pip install anthropic")

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.anthropic = Anthropic(api_key=settings.anthropic_api_key)
        logger.info("✓ Anthropic (Claude) client initialized")

        # Initialize OpenAI client (OPTIONAL - controlled by OPENAI_ENABLED)
        self.openai = None
        self.openai_enabled = getattr(settings, 'openai_enabled', True)

        if self.openai_enabled:
            if not OpenAI:
                logger.warning("OpenAI library not installed - GPT-4 entity extraction disabled")
                self.openai_enabled = False
            elif not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY not configured - GPT-4 entity extraction disabled")
                self.openai_enabled = False
            else:
                self.openai = OpenAI(api_key=settings.openai_api_key)
                logger.info("✓ OpenAI (GPT-4) client initialized - Hybrid mode enabled")
        else:
            logger.info("ℹ OpenAI disabled via OPENAI_ENABLED=false - Claude-only mode")

        # Configuration
        self.max_retries = getattr(settings, 'ai_max_retries', 3)
        self.daily_budget_usd = getattr(settings, 'ai_daily_budget_usd', 100.0)

        # Cost tracking (in-memory, for production use Redis or database)
        self._daily_costs = {}
        self._last_reset = datetime.utcnow().date()

    def _reset_daily_costs_if_needed(self):
        """Reset daily costs if it's a new day"""
        today = datetime.utcnow().date()
        if today > self._last_reset:
            self._daily_costs = {}
            self._last_reset = today
            logger.info("Daily AI costs reset")

    def _track_cost(self, cost_usd: float):
        """Track API cost"""
        self._reset_daily_costs_if_needed()
        today = datetime.utcnow().date().isoformat()
        self._daily_costs[today] = self._daily_costs.get(today, 0.0) + cost_usd

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        input_price: float,
        output_price: float
    ) -> float:
        """Calculate cost based on token usage"""
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        return input_cost + output_cost

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Retry function with exponential backoff

        Args:
            func: Async function to retry
            *args, **kwargs: Arguments for function

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except (AnthropicRateLimitError, OpenAIRateLimitError) as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                logger.warning(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error in attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)

    async def analyze_with_claude(self, text: str, doc_type: str) -> dict:
        """
        Analyze document using Claude 3.5 Sonnet

        Provides:
        - Concise summary (3-5 sentences)
        - Document classification
        - Key points extraction
        - Confidence rating

        Args:
            text: Document text to analyze
            doc_type: Document MIME type

        Returns:
            dict with summary, classification, confidence, key_points, model, tokens, cost
        """
        # Truncate text if too long (Claude supports up to 200k tokens)
        max_chars = 100000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated due to length...]"

        prompt = f"""You are analyzing a legal document. Please provide:

1. A concise summary (3-5 sentences) of the document's content and purpose
2. Classification of the document type (e.g., Chargesheet, FIR, Court Order, Affidavit, Evidence Document, Legal Notice, etc.)
3. 3-5 key points or important facts from the document
4. Your confidence level in the classification (0-1 scale)

Document text:
{text}

Please respond in the following JSON format:
{{
    "summary": "Your 3-5 sentence summary here",
    "classification": "Document type",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "confidence": 0.95
}}"""

        async def _call_claude():
            response = self.anthropic.messages.create(
                model=self.CLAUDE_MODEL,
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response

        try:
            response = await self._retry_with_backoff(_call_claude)

            # Extract JSON from response
            content = response.content[0].text

            # Try to parse JSON from response
            try:
                # Find JSON in response (Claude sometimes adds explanation text)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
                # Fallback: create structured response from text
                result = {
                    "summary": content[:500],
                    "classification": "Unknown",
                    "key_points": ["Analysis completed but response format was unexpected"],
                    "confidence": 0.5
                }

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(
                input_tokens,
                output_tokens,
                self.CLAUDE_INPUT_PRICE,
                self.CLAUDE_OUTPUT_PRICE
            )

            self._track_cost(cost)

            logger.info(f"Claude analysis complete: {input_tokens} input, {output_tokens} output tokens, ${cost:.4f}")

            return {
                **result,
                "model": self.CLAUDE_MODEL,
                "tokens_used": input_tokens + output_tokens,
                "cost_usd": round(cost, 5)
            }

        except Exception as e:
            logger.error(f"Claude analysis failed: {str(e)}")
            raise

    async def extract_entities_with_gpt4(self, text: str) -> dict:
        """
        Extract structured entities using GPT-4

        Extracts:
        - People (names and roles)
        - Dates
        - Locations
        - Case numbers
        - Organizations

        Args:
            text: Document text to analyze

        Returns:
            dict with entities, model, tokens, cost
        """
        # Truncate text if too long
        max_chars = 80000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated due to length...]"

        system_prompt = """You are a legal document entity extraction system. Extract all relevant entities from the provided legal document text.

Extract the following:
- people: Array of objects with 'name' (full name), 'role' (Accused, Victim, Witness, Judge, Lawyer, etc.), and 'confidence' (0-1)
- dates: Array of date strings in YYYY-MM-DD format or as mentioned in document
- locations: Array of location names (cities, addresses, courts, etc.)
- case_numbers: Array of case/FIR numbers
- organizations: Array of organization names (police stations, courts, companies, etc.)

Be precise and only extract entities that are clearly mentioned in the text."""

        user_prompt = f"""Extract entities from this legal document:

{text}

Return ONLY a valid JSON object with no additional text."""

        async def _call_gpt4():
            response = self.openai.chat.completions.create(
                model=self.GPT4_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000
            )
            return response

        try:
            response = await self._retry_with_backoff(_call_gpt4)

            # Parse JSON response
            content = response.choices[0].message.content
            entities = json.loads(content)

            # Ensure all expected keys exist
            entities.setdefault("people", [])
            entities.setdefault("dates", [])
            entities.setdefault("locations", [])
            entities.setdefault("case_numbers", [])
            entities.setdefault("organizations", [])

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self._calculate_cost(
                input_tokens,
                output_tokens,
                self.GPT4_INPUT_PRICE,
                self.GPT4_OUTPUT_PRICE
            )

            self._track_cost(cost)

            logger.info(f"GPT-4 entity extraction complete: {input_tokens} input, {output_tokens} output tokens, ${cost:.4f}")

            return {
                **entities,
                "model": self.GPT4_MODEL,
                "tokens_used": input_tokens + output_tokens,
                "cost_usd": round(cost, 5)
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 response as JSON: {str(e)}")
            return {
                "people": [],
                "dates": [],
                "locations": [],
                "case_numbers": [],
                "organizations": [],
                "model": self.GPT4_MODEL,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "error": "Failed to parse response"
            }
        except Exception as e:
            logger.error(f"GPT-4 entity extraction failed: {str(e)}")
            raise

    async def process_document(self, text: str, doc_type: str) -> dict:
        """
        Complete document processing pipeline

        Standard: Runs Claude analysis + GPT-4 entity extraction in parallel (hybrid approach)
        Fallback: If GPT-4 fails (quota/auth), continues with Claude-only mode

        Args:
            text: Document text
            doc_type: Document MIME type

        Returns:
            dict with analysis results, entities, and total cost
        """
        if not text or len(text.strip()) < 50:
            raise ValueError("Text is too short for meaningful analysis")

        logger.info(f"Starting document processing: {len(text)} characters")

        # Determine processing mode
        if self.openai_enabled:
            logger.info("STANDARD MODE: Running hybrid AI (Claude + GPT-4)")
        else:
            logger.info("CLAUDE-ONLY MODE: GPT-4 disabled (OPENAI_ENABLED=false)")

        try:
            # Run Claude analysis (REQUIRED - failure stops everything)
            analysis_result = await self.analyze_with_claude(text, doc_type)
            logger.info(f"✓ Claude analysis complete: ${analysis_result['cost_usd']:.4f}")

            # Run GPT-4 entity extraction (OPTIONAL - skip if disabled)
            entities_result = None
            gpt4_fallback_reason = None

            if not self.openai_enabled:
                # Explicitly disabled - not a failure, just not configured
                gpt4_fallback_reason = "GPT-4 disabled via OPENAI_ENABLED config"
                logger.info(f"ℹ Skipping GPT-4 entity extraction: {gpt4_fallback_reason}")
                entities_result = {
                    "people": [],
                    "dates": [],
                    "locations": [],
                    "case_numbers": [],
                    "organizations": [],
                    "model": "disabled",
                    "cost_usd": 0.0,
                    "fallback_reason": gpt4_fallback_reason
                }
            else:
                # Try GPT-4 extraction
                try:
                    entities_result = await self.extract_entities_with_gpt4(text)
                    logger.info(f"✓ GPT-4 entity extraction complete: ${entities_result['cost_usd']:.4f}")
                except Exception as e:
                    error_str = str(e)

                    # Check if it's a known fallback scenario (quota/auth issues)
                    if "insufficient_quota" in error_str or "quota" in error_str.lower():
                        gpt4_fallback_reason = "OpenAI API quota exceeded"
                        logger.warning(f"⚠ FALLBACK MODE ACTIVATED: {gpt4_fallback_reason}")
                        logger.warning("⚠ Continuing with Claude-only analysis (entity extraction unavailable)")
                    elif "401" in error_str or "authentication" in error_str.lower():
                        gpt4_fallback_reason = "OpenAI API authentication failed"
                        logger.warning(f"⚠ FALLBACK MODE ACTIVATED: {gpt4_fallback_reason}")
                        logger.warning("⚠ Continuing with Claude-only analysis (entity extraction unavailable)")
                    else:
                        # Unknown error - still fallback but log as error
                        gpt4_fallback_reason = f"GPT-4 error: {error_str[:100]}"
                        logger.error(f"⚠ FALLBACK MODE ACTIVATED: Unexpected GPT-4 error")
                        logger.error(f"Error details: {error_str}")
                        logger.warning("⚠ Continuing with Claude-only analysis")

                    # Create fallback empty entities with clear indication
                    entities_result = {
                        "people": [],
                        "dates": [],
                        "locations": [],
                        "case_numbers": [],
                        "organizations": [],
                        "model": "unavailable",
                        "cost_usd": 0.0,
                        "fallback_reason": gpt4_fallback_reason
                    }

            total_cost = analysis_result["cost_usd"] + entities_result["cost_usd"]

            if gpt4_fallback_reason:
                logger.warning(f"✓ Document processing complete (FALLBACK MODE): Total cost ${total_cost:.4f} (Claude only)")
            else:
                logger.info(f"✓ Document processing complete (STANDARD MODE): Total cost ${total_cost:.4f} (Claude + GPT-4)")

            return {
                "analysis": {
                    "summary": analysis_result["summary"],
                    "classification": analysis_result["classification"],
                    "confidence": analysis_result["confidence"],
                    "key_points": analysis_result["key_points"],
                    "model": analysis_result["model"]
                },
                "entities": {
                    "people": entities_result.get("people", []),
                    "dates": entities_result.get("dates", []),
                    "locations": entities_result.get("locations", []),
                    "case_numbers": entities_result.get("case_numbers", []),
                    "organizations": entities_result.get("organizations", []),
                    "model": entities_result["model"],
                    "fallback_reason": entities_result.get("fallback_reason")  # Only present if fallback occurred
                },
                "total_cost": round(total_cost, 5),
                "model_versions": {
                    "claude": analysis_result["model"],
                    "gpt4": entities_result["model"],
                    "claude_cost": analysis_result["cost_usd"],
                    "gpt4_cost": entities_result["cost_usd"],
                    "mode": "fallback" if gpt4_fallback_reason else "standard"
                }
            }

        except Exception as e:
            # Claude failed - this is a hard failure
            logger.error(f"✗ Document processing FAILED: {str(e)}")
            logger.error("Claude analysis is required and failed - cannot continue")
            raise

    def estimate_cost(self, text_length: int) -> float:
        """
        Estimate processing cost based on text length

        Args:
            text_length: Number of characters in text

        Returns:
            Estimated cost in USD
        """
        # Rough estimate: ~4 chars per token
        estimated_tokens = text_length // 4

        # Claude: input tokens + ~500 output tokens
        claude_cost = self._calculate_cost(
            estimated_tokens,
            500,
            self.CLAUDE_INPUT_PRICE,
            self.CLAUDE_OUTPUT_PRICE
        )

        # GPT-4: input tokens + ~300 output tokens
        gpt4_cost = self._calculate_cost(
            estimated_tokens,
            300,
            self.GPT4_INPUT_PRICE,
            self.GPT4_OUTPUT_PRICE
        )

        return round(claude_cost + gpt4_cost, 5)

    def check_daily_budget(self) -> Tuple[bool, float]:
        """
        Check if within daily budget

        Returns:
            (within_budget, remaining_budget_usd)
        """
        self._reset_daily_costs_if_needed()
        today = datetime.utcnow().date().isoformat()
        spent = self._daily_costs.get(today, 0.0)
        remaining = self.daily_budget_usd - spent

        return remaining > 0, round(remaining, 2)

    def get_daily_usage(self) -> dict:
        """
        Get current daily usage statistics

        Returns:
            dict with spent, budget, remaining, percentage
        """
        self._reset_daily_costs_if_needed()
        today = datetime.utcnow().date().isoformat()
        spent = self._daily_costs.get(today, 0.0)
        remaining = max(0, self.daily_budget_usd - spent)
        percentage = (spent / self.daily_budget_usd * 100) if self.daily_budget_usd > 0 else 0

        return {
            "spent_usd": round(spent, 2),
            "budget_usd": self.daily_budget_usd,
            "remaining_usd": round(remaining, 2),
            "percentage_used": round(percentage, 1),
            "date": today
        }


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    Get singleton instance of AIService

    Returns:
        AIService instance
    """
    global _ai_service

    if _ai_service is None:
        _ai_service = AIService()

    return _ai_service
