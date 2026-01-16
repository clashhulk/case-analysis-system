"""Cost tracking service for monitoring AI usage"""
import logging
from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import AICostTracking

logger = logging.getLogger(__name__)


class CostTrackingService:
    """Service for tracking AI costs in database"""

    @staticmethod
    def track_cost(
        db: Session,
        service_type: str,
        model_name: str,
        cost_usd: float,
        document_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        extra_data: Optional[dict] = None
    ) -> AICostTracking:
        """
        Track AI service cost in database

        Args:
            db: Database session
            service_type: Type of service ('text_analysis', 'entity_extraction', 'vision_ai')
            model_name: Name of the model used
            cost_usd: Cost in USD
            document_id: Associated document ID
            case_id: Associated case ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration_ms: Duration in milliseconds
            success: Whether the operation succeeded
            error_message: Error message if failed
            extra_data: Additional metadata

        Returns:
            AICostTracking record
        """
        try:
            record = AICostTracking(
                document_id=document_id,
                case_id=case_id,
                service_type=service_type,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                extra_data=extra_data
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            logger.info(
                f"Tracked cost: {service_type} | {model_name} | "
                f"${cost_usd:.4f} | doc={document_id} | case={case_id}"
            )

            return record

        except Exception as e:
            logger.error(f"Failed to track cost: {str(e)}")
            db.rollback()
            raise


# Singleton instance
_cost_tracking_service: Optional[CostTrackingService] = None


def get_cost_tracking_service() -> CostTrackingService:
    """Get singleton instance"""
    global _cost_tracking_service
    if _cost_tracking_service is None:
        _cost_tracking_service = CostTrackingService()
    return _cost_tracking_service
