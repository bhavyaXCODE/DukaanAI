from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from app.core.database import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.models.transaction import Transaction

router = APIRouter()


@router.get("/summary")
async def get_summary_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    query = select(Transaction).where(
        Transaction.shop_id == shop_id,
        Transaction.status == "CONFIRMED",
    )

    if date_from:
        try:
            query = query.where(Transaction.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(Transaction.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    credit_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).select_from(
            query.where(Transaction.type == "CREDIT").subquery()
        )
    )
    total_credit = float(credit_res.scalar() or 0.0)

    payment_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).select_from(
            query.where(Transaction.type == "PAYMENT").subquery()
        )
    )
    total_payments = float(payment_res.scalar() or 0.0)

    count_res = await db.execute(
        select(func.count(Transaction.id)).select_from(query.subquery())
    )
    tx_count = int(count_res.scalar() or 0)

    return {
        "total_credit": round(total_credit, 2),
        "total_payments": round(total_payments, 2),
        "net": round(total_credit - total_payments, 2),
        "transaction_count": tx_count,
        "date_from": date_from,
        "date_to": date_to,
    }


@router.get("/customers")
async def get_customer_report(
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            Customer.id,
            Customer.name,
            Customer.alias,
            Customer.phone,
            Customer.landmark,
            Customer.outstanding_balance,
            func.coalesce(
                func.sum(
                    case((Transaction.type == "CREDIT", Transaction.amount), else_=0)
                ),
                0,
            ).label("total_credit"),
            func.coalesce(
                func.sum(
                    case((Transaction.type == "PAYMENT", Transaction.amount), else_=0)
                ),
                0,
            ).label("total_payments"),
        )
        .outerjoin(
            Transaction,
            (Transaction.customer_id == Customer.id) & (Transaction.status == "CONFIRMED"),
        )
        .where(Customer.shop_id == shop_id, Customer.is_active == True)
        .group_by(Customer.id)
        .order_by(desc(Customer.outstanding_balance))
    )

    result = await db.execute(stmt)
    rows = result.all()

    report: List[Dict[str, Any]] = []
    for r in rows:
        report.append(
            {
                "id": r.id,
                "name": r.name,
                "alias": r.alias,
                "phone": r.phone,
                "landmark": r.landmark,
                "outstanding_balance": float(r.outstanding_balance),
                "total_credit": float(r.total_credit),
                "total_payments": float(r.total_payments),
            }
        )

    return report


@router.get("/daily")
async def get_daily_report(
    days: int = Query(default=30, ge=1, le=90),
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    results = []

    for i in range(days - 1, -1, -1):
        day_date = now - timedelta(days=i)
        day_start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        credit_res = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.shop_id == shop_id,
                Transaction.status == "CONFIRMED",
                Transaction.type == "CREDIT",
                Transaction.created_at >= day_start,
                Transaction.created_at < day_end,
            )
        )
        credit = float(credit_res.scalar() or 0.0)

        payment_res = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.shop_id == shop_id,
                Transaction.status == "CONFIRMED",
                Transaction.type == "PAYMENT",
                Transaction.created_at >= day_start,
                Transaction.created_at < day_end,
            )
        )
        payment = float(payment_res.scalar() or 0.0)

        results.append(
            {
                "date": day_start.strftime("%Y-%m-%d"),
                "credit": round(credit, 2),
                "payment": round(payment, 2),
                "net": round(credit - payment, 2),
            }
        )

    return results
