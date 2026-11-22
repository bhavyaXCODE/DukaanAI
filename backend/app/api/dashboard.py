from datetime import datetime, timedelta, timezone
from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.core.database import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.schemas.transaction import DashboardStats, DailyChartPoint

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    yesterday_start = today_start - timedelta(days=1)

    # 1. Total outstanding balance across active customers
    # Dynamically calculated from confirmed transactions in the ledger
    cust_stmt = select(Customer).where(
        Customer.shop_id == shop_id,
        Customer.is_active == True,
    )
    cust_res = await db.execute(cust_stmt)
    customers = cust_res.scalars().all()

    total_outstanding = Decimal("0.00")
    for c in customers:
        tx_rows_stmt = select(Transaction.type, Transaction.amount).where(
            Transaction.customer_id == c.id,
            Transaction.status == "CONFIRMED"
        ).order_by(Transaction.created_at.asc(), Transaction.id.asc())
        tx_rows_res = await db.execute(tx_rows_stmt)
        tx_rows = tx_rows_res.all()

        running_bal = Decimal("0.00")
        for t_type, t_amt in tx_rows:
            if t_type == "CREDIT":
                running_bal += Decimal(str(t_amt))
            elif t_type == "PAYMENT":
                running_bal = max(Decimal("0.00"), running_bal - Decimal(str(t_amt)))

        if c.outstanding_balance != running_bal:
            c.outstanding_balance = running_bal
        total_outstanding += running_bal

    await db.commit()

    # 2. Active customers count
    active_customers = len(customers)

    # 3. Credit today & payments today
    credit_today_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.shop_id == shop_id,
            Transaction.status == "CONFIRMED",
            Transaction.type == "CREDIT",
            Transaction.created_at >= today_start,
        )
    )
    credit_today = float(credit_today_res.scalar() or 0.0)

    credit_yest_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.shop_id == shop_id,
            Transaction.status == "CONFIRMED",
            Transaction.type == "CREDIT",
            Transaction.created_at >= yesterday_start,
            Transaction.created_at < today_start,
        )
    )
    credit_yesterday = float(credit_yest_res.scalar() or 0.0)

    # Credit % change
    if credit_yesterday > 0:
        credit_today_pct_change = round(((credit_today - credit_yesterday) / credit_yesterday) * 100, 1)
    elif credit_today > 0:
        credit_today_pct_change = 100.0
    else:
        credit_today_pct_change = 0.0

    # 4. Payments today & yesterday
    payments_today_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.shop_id == shop_id,
            Transaction.status == "CONFIRMED",
            Transaction.type == "PAYMENT",
            Transaction.created_at >= today_start,
        )
    )
    payments_today = float(payments_today_res.scalar() or 0.0)

    payments_yest_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.shop_id == shop_id,
            Transaction.status == "CONFIRMED",
            Transaction.type == "PAYMENT",
            Transaction.created_at >= yesterday_start,
            Transaction.created_at < today_start,
        )
    )
    payments_yesterday = float(payments_yest_res.scalar() or 0.0)

    # Payments % change
    if payments_yesterday > 0:
        payments_today_pct_change = round(((payments_today - payments_yesterday) / payments_yesterday) * 100, 1)
    elif payments_today > 0:
        payments_today_pct_change = 100.0
    else:
        payments_today_pct_change = 0.0

    # 5. Confirmed transactions count today
    tx_today_res = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.shop_id == shop_id,
            Transaction.status == "CONFIRMED",
            Transaction.created_at >= today_start,
        )
    )
    transactions_today = int(tx_today_res.scalar() or 0)

    return DashboardStats(
        total_outstanding=float(round(total_outstanding, 2)),
        credit_today=round(credit_today, 2),
        credit_today_pct_change=credit_today_pct_change,
        payments_today=round(payments_today, 2),
        payments_today_pct_change=payments_today_pct_change,
        active_customers=active_customers,
        transactions_today=transactions_today,
    )


@router.get("/chart", response_model=List[DailyChartPoint])
async def get_dashboard_chart(
    days: int = Query(default=7, ge=1, le=30),
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    points: List[DailyChartPoint] = []

    # Iterate over the last `days` days in chronological order
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

        points.append(
            DailyChartPoint(
                date=day_start.strftime("%Y-%m-%d"),
                day=day_start.strftime("%a"),
                credit=round(credit, 2),
                payment=round(payment, 2),
            )
        )

    return points
