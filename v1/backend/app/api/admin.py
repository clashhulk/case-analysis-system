"""Admin API endpoints for cost tracking and system management"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.db.database import get_db
from app.db.models import AICostTracking

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/costs/summary")
def get_cost_summary(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get cost summary for specified period

    Returns:
    - Total spend
    - Spend by service type
    - Spend by model
    - Daily breakdown
    """
    since_date = datetime.utcnow() - timedelta(days=days)

    # Total cost
    total_cost = db.query(
        func.sum(AICostTracking.cost_usd)
    ).filter(
        AICostTracking.created_at >= since_date
    ).scalar() or 0

    # Cost by service type
    costs_by_service = db.query(
        AICostTracking.service_type,
        func.sum(AICostTracking.cost_usd).label('total_cost'),
        func.count(AICostTracking.id).label('request_count'),
        func.sum(AICostTracking.input_tokens).label('total_input_tokens'),
        func.sum(AICostTracking.output_tokens).label('total_output_tokens')
    ).filter(
        AICostTracking.created_at >= since_date
    ).group_by(
        AICostTracking.service_type
    ).all()

    # Cost by model
    costs_by_model = db.query(
        AICostTracking.model_name,
        func.sum(AICostTracking.cost_usd).label('total_cost'),
        func.count(AICostTracking.id).label('request_count')
    ).filter(
        AICostTracking.created_at >= since_date
    ).group_by(
        AICostTracking.model_name
    ).all()

    # Daily breakdown
    daily_costs = db.query(
        func.date(AICostTracking.created_at).label('date'),
        func.sum(AICostTracking.cost_usd).label('total_cost'),
        func.count(AICostTracking.id).label('request_count')
    ).filter(
        AICostTracking.created_at >= since_date
    ).group_by(
        func.date(AICostTracking.created_at)
    ).order_by(
        desc('date')
    ).all()

    return {
        "period_days": days,
        "since_date": since_date.isoformat(),
        "total_cost_usd": float(total_cost),
        "costs_by_service": [
            {
                "service_type": row.service_type,
                "total_cost_usd": float(row.total_cost),
                "request_count": row.request_count,
                "total_input_tokens": row.total_input_tokens,
                "total_output_tokens": row.total_output_tokens
            }
            for row in costs_by_service
        ],
        "costs_by_model": [
            {
                "model_name": row.model_name,
                "total_cost_usd": float(row.total_cost),
                "request_count": row.request_count
            }
            for row in costs_by_model
        ],
        "daily_breakdown": [
            {
                "date": row.date.isoformat(),
                "total_cost_usd": float(row.total_cost),
                "request_count": row.request_count
            }
            for row in daily_costs
        ]
    }


@router.get("/costs/recent")
def get_recent_costs(
    limit: int = Query(default=50, ge=1, le=1000, description="Number of recent records"),
    service_type: Optional[str] = Query(default=None, description="Filter by service type"),
    db: Session = Depends(get_db)
):
    """
    Get recent cost tracking records

    Useful for monitoring real-time AI usage
    """
    query = db.query(AICostTracking)

    if service_type:
        query = query.filter(AICostTracking.service_type == service_type)

    records = query.order_by(
        desc(AICostTracking.created_at)
    ).limit(limit).all()

    return {
        "records": [
            {
                "id": str(record.id),
                "service_type": record.service_type,
                "model_name": record.model_name,
                "cost_usd": float(record.cost_usd),
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "duration_ms": record.duration_ms,
                "success": record.success,
                "document_id": str(record.document_id) if record.document_id else None,
                "case_id": str(record.case_id) if record.case_id else None,
                "created_at": record.created_at.isoformat()
            }
            for record in records
        ],
        "total_records": len(records)
    }


@router.get("/costs/stats")
def get_cost_stats(db: Session = Depends(get_db)):
    """
    Get overall statistics

    Returns high-level metrics
    """
    # Today's cost
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cost = db.query(
        func.sum(AICostTracking.cost_usd)
    ).filter(
        AICostTracking.created_at >= today_start
    ).scalar() or 0

    # This week's cost
    week_start = datetime.utcnow() - timedelta(days=7)
    week_cost = db.query(
        func.sum(AICostTracking.cost_usd)
    ).filter(
        AICostTracking.created_at >= week_start
    ).scalar() or 0

    # This month's cost
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cost = db.query(
        func.sum(AICostTracking.cost_usd)
    ).filter(
        AICostTracking.created_at >= month_start
    ).scalar() or 0

    # Total requests today
    today_requests = db.query(
        func.count(AICostTracking.id)
    ).filter(
        AICostTracking.created_at >= today_start
    ).scalar() or 0

    # Success rate today
    today_success = db.query(
        func.count(AICostTracking.id)
    ).filter(
        AICostTracking.created_at >= today_start,
        AICostTracking.success == True
    ).scalar() or 0

    success_rate = (today_success / today_requests * 100) if today_requests > 0 else 100

    return {
        "today": {
            "cost_usd": float(today_cost),
            "requests": today_requests,
            "success_rate": round(success_rate, 2)
        },
        "this_week": {
            "cost_usd": float(week_cost)
        },
        "this_month": {
            "cost_usd": float(month_cost)
        }
    }
