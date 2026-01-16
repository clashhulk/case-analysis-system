"""Vision AI service for analyzing documents with poor text quality

Uses Claude Vision API to extract structured data from document images
when standard text extraction fails (quality < 0.5).

Supports:
- PDF to image conversion
- Scanned documents with handwriting
- Low-quality scans with poor OCR
- Form-based documents
"""
import base64
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app.config import get_settings

logger = logging.getLogger(__name__)


class VisionAIService:
    """Service for Vision AI-powered document analysis"""

    # Model for vision analysis
    VISION_MODEL = "claude-sonnet-4-20250514"  # Latest Claude with vision

    # Pricing per 1M tokens
    INPUT_PRICE_PER_M = 3.00
    OUTPUT_PRICE_PER_M = 15.00

    # Image pricing (approximate token cost per image)
    TOKENS_PER_IMAGE = 1500  # Rough estimate for a document page

    def __init__(self):
        """Initialize Vision AI service"""
        settings = get_settings()

        if not Anthropic:
            raise ImportError("anthropic library required. Install: pip install anthropic")

        if not fitz:
            raise ImportError("PyMuPDF required. Install: pip install pymupdf")

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.anthropic = Anthropic(api_key=settings.anthropic_api_key)
        self.enabled = getattr(settings, 'vision_ai_enabled', True)
        self.quality_threshold = getattr(settings, 'vision_ai_quality_threshold', 0.5)
        self.max_pages = getattr(settings, 'vision_ai_max_pages', 10)

        logger.info("Vision AI service initialized")

    def convert_pdf_to_images(self, pdf_path: str, max_pages: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Convert PDF pages to base64-encoded images

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to convert (None = all)

        Returns:
            List of dicts with page_number and base64_data
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        max_pages = max_pages or self.max_pages
        images = []

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            pages_to_process = min(total_pages, max_pages)

            logger.info(f"Converting {pages_to_process} pages from PDF to images")

            for page_num in range(pages_to_process):
                page = doc[page_num]

                # Render page to image (150 DPI for good quality vs cost balance)
                pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))

                # Convert to PNG bytes
                img_bytes = pix.tobytes("png")

                # Encode to base64
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                images.append({
                    "page_number": page_num + 1,
                    "base64_data": img_base64,
                    "width": pix.width,
                    "height": pix.height
                })

            doc.close()

            logger.info(f"Successfully converted {len(images)} pages to images")
            return images

        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {str(e)}")
            raise ValueError(f"PDF to image conversion failed: {str(e)}")

    def analyze_document_with_vision(
        self,
        images: List[Dict[str, any]],
        document_type: str = "legal"
    ) -> Dict:
        """
        Analyze document images using Claude Vision

        Args:
            images: List of page images (from convert_pdf_to_images)
            document_type: Type of document for context

        Returns:
            dict with extracted text, entities, and metadata
        """
        if not self.enabled:
            raise RuntimeError("Vision AI is disabled")

        if not images:
            raise ValueError("No images provided")

        try:
            # Build prompt for legal document analysis
            system_prompt = """You are an expert document analyst specializing in legal documents.
Extract ALL text, data, and information from the provided document images with high accuracy.

For each document, extract:
1. Full text content (preserve formatting, layout, structure)
2. Key entities: names, dates, case numbers, locations, organizations
3. Document metadata: type, title, parties involved
4. Form fields: labels and values
5. Handwritten content (if any)

Return results as valid JSON."""

            user_prompt = f"""Analyze this {document_type} document and extract information.

CRITICAL: Return ONLY valid JSON. Do not include any markdown formatting, code blocks, or explanatory text.

Extract:
- Complete text content (preserve all text from the document)
- Names of people and their roles
- Important dates
- Case/file numbers
- Locations
- Organizations/companies
- Any form fields and their values

Return this exact JSON structure:
{{
    "text": "full extracted text...",
    "document_type": "type classification",
    "entities": {{
        "people": [{{"name": "...", "role": "..."}}],
        "dates": ["..."],
        "case_numbers": ["..."],
        "locations": ["..."],
        "organizations": ["..."]
    }},
    "form_fields": {{"field_name": "value"}},
    "confidence": 0.0-1.0
}}

Remember: Return ONLY the JSON object, nothing else."""

            # Build message content with images
            content = []
            for img in images[:self.max_pages]:  # Respect max pages limit
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img["base64_data"]
                    }
                })

            # Add text prompt after images
            content.append({
                "type": "text",
                "text": user_prompt
            })

            # Call Claude Vision API
            logger.info(f"Calling Claude Vision API with {len(images)} images")
            start_time = datetime.utcnow()

            response = self.anthropic.messages.create(
                model=self.VISION_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Extract response
            response_text = response.content[0].text

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = (
                (input_tokens / 1_000_000) * self.INPUT_PRICE_PER_M +
                (output_tokens / 1_000_000) * self.OUTPUT_PRICE_PER_M
            )

            logger.info(
                f"Vision AI complete: {input_tokens} in, {output_tokens} out, "
                f"${cost_usd:.4f}, {duration_ms:.0f}ms"
            )

            # Parse JSON response
            try:
                # Try direct JSON parsing first
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(1))
                        logger.info("Extracted JSON from markdown code block")
                    except json.JSONDecodeError:
                        logger.warning("Response not valid JSON, using raw text")
                        extracted_data = {
                            "text": response_text,
                            "entities": {},
                            "confidence": 0.7
                        }
                else:
                    # If response is not valid JSON, use raw text
                    logger.warning("Response not valid JSON, using raw text")
                    extracted_data = {
                        "text": response_text,
                        "entities": {},
                        "confidence": 0.7
                    }

            # Return structured result
            return {
                "success": True,
                "text": extracted_data.get("text", ""),
                "text_length": len(extracted_data.get("text", "")),
                "method": "vision-ai",
                "metadata": {
                    "model": self.VISION_MODEL,
                    "pages_processed": len(images),
                    "document_type": extracted_data.get("document_type"),
                    "entities": extracted_data.get("entities", {}),
                    "form_fields": extracted_data.get("form_fields", {}),
                    "confidence": extracted_data.get("confidence", 0.8),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_ms": duration_ms,
                    "cost_usd": round(cost_usd, 4)
                }
            }

        except Exception as e:
            logger.error(f"Vision AI analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "text_length": 0,
                "method": "vision-ai-failed"
            }

    def analyze_document(self, pdf_path: str, document_type: str = "legal") -> Dict:
        """
        Main entry point: convert PDF to images and analyze with Vision AI

        Args:
            pdf_path: Path to PDF file
            document_type: Type of document (legal, form, contract, etc.)

        Returns:
            dict with analysis results
        """
        try:
            # Step 1: Convert PDF to images
            images = self.convert_pdf_to_images(pdf_path)

            if not images:
                return {
                    "success": False,
                    "error": "No images extracted from PDF",
                    "text": "",
                    "method": "vision-ai-failed"
                }

            # Step 2: Analyze with Vision AI
            result = self.analyze_document_with_vision(images, document_type)

            # Add extraction timestamp
            result["extracted_at"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            logger.error(f"Vision AI document analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "text_length": 0,
                "method": "vision-ai-failed",
                "extracted_at": datetime.utcnow().isoformat()
            }


# Singleton instance
_vision_ai_service: Optional[VisionAIService] = None


def get_vision_ai_service() -> VisionAIService:
    """
    Get singleton instance of VisionAIService

    Returns:
        VisionAIService instance
    """
    global _vision_ai_service

    if _vision_ai_service is None:
        _vision_ai_service = VisionAIService()

    return _vision_ai_service
