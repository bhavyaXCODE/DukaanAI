from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from app.core.database import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.promise import PaymentPromise
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionListResponse,
)

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=500),
    customer_id: Optional[int] = None,
    type: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size
    query = (
        select(Transaction, Customer.name.label("customer_name"))
        .join(Customer, Transaction.customer_id == Customer.id)
        .where(Transaction.shop_id == shop_id)
    )

    if customer_id:
        query = query.where(Transaction.customer_id == customer_id)
    if type:
        query = query.where(Transaction.type == type.upper())
    if status_filter:
        query = query.where(Transaction.status == status_filter.upper())
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(Transaction.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(Transaction.created_at <= dt_to)
        except ValueError:
            pass

    # Total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paginate
    query = query.order_by(desc(Transaction.created_at)).offset(offset).limit(size)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for tx, cust_name in rows:
        tx_data = TransactionResponse.model_validate(tx)
        tx_data.customer_name = cust_name
        items.append(tx_data)

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    tx_in: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify customer
    customer = None
    if tx_in.customer_id:
        cust_res = await db.execute(select(Customer).where(Customer.id == tx_in.customer_id))
        customer = cust_res.scalar_one_or_none()

    if not customer and tx_in.customer_name:
        clean_name = tx_in.customer_name.strip()
        cust_res = await db.execute(
            select(Customer).where(
                Customer.shop_id == (tx_in.shop_id or settings.SHOP_ID),
                Customer.name.ilike(clean_name)
            )
        )
        customer = cust_res.scalar_one_or_none()
        if not customer:
            customer = Customer(
                shop_id=tx_in.shop_id or settings.SHOP_ID,
                name=clean_name,
                outstanding_balance=Decimal("0.00"),
                is_active=True,
            )
            db.add(customer)
            await db.flush()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found or customer_name required")

    amount = Decimal(str(tx_in.amount))
    tx_type = tx_in.type.upper()
    if tx_type not in ("CREDIT", "PAYMENT"):
        raise HTTPException(status_code=400, detail="Transaction type must be CREDIT or PAYMENT")

    now = datetime.now(timezone.utc)
    transaction = Transaction(
        shop_id=tx_in.shop_id or settings.SHOP_ID,
        customer_id=customer.id,
        type=tx_type,
        amount=amount,
        description=tx_in.description,
        voice_transcript=tx_in.voice_transcript,
        status="CONFIRMED",
        created_at=now,
        confirmed_at=now,
    )
    db.add(transaction)

    # Update balance
    curr_bal = float(customer.outstanding_balance)
    if tx_type == "CREDIT":
        new_bal = curr_bal + float(amount)
    else:
        new_bal = max(0.0, curr_bal - float(amount))

        # Auto-fulfill pending promise for this customer if payment covers it
        p_res = await db.execute(
            select(PaymentPromise).where(
                PaymentPromise.customer_id == customer.id,
                PaymentPromise.status == "PENDING"
            ).order_by(PaymentPromise.id.asc())
        )
        pending_promises = p_res.scalars().all()
        for p in pending_promises:
            if float(amount) >= float(p.amount):
                p.status = "FULFILLED"
                if customer.promised_amount == p.amount:
                    remaining_p = [pr for pr in pending_promises if pr.id != p.id]
                    if remaining_p:
                        customer.promised_amount = remaining_p[0].amount
                        customer.promised_date = remaining_p[0].promise_date
                        customer.promise_notes = f"Promised ₹{float(remaining_p[0].amount):,.0f} on {remaining_p[0].promise_date}"
                    else:
                        customer.promised_amount = Decimal("0.00")
                        customer.promised_date = None
                        customer.promise_notes = None
                break

    customer.outstanding_balance = Decimal(str(round(new_bal, 2)))

    await db.commit()
    await db.refresh(transaction)

    resp = TransactionResponse.model_validate(transaction)
    resp.customer_name = customer.name
    return resp


@router.put("/{tx_id}/confirm", response_model=TransactionResponse)
async def confirm_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status == "CONFIRMED":
        cust_res = await db.execute(select(Customer).where(Customer.id == tx.customer_id))
        cust = cust_res.scalar_one_or_none()
        resp = TransactionResponse.model_validate(tx)
        resp.customer_name = cust.name if cust else None
        return resp

    # Fetch customer
    cust_res = await db.execute(select(Customer).where(Customer.id == tx.customer_id))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Update status and balance
    tx.status = "CONFIRMED"
    tx.confirmed_at = datetime.now(timezone.utc)

    curr_bal = float(customer.outstanding_balance)
    amount = float(tx.amount)
    if tx.type == "CREDIT":
        new_bal = curr_bal + amount
    else:
        new_bal = max(0.0, curr_bal - amount)

    customer.outstanding_balance = Decimal(str(round(new_bal, 2)))

    await db.commit()
    await db.refresh(tx)

    resp = TransactionResponse.model_validate(tx)
    resp.customer_name = customer.name
    return resp


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    tx_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status == "CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete confirmed transaction. Please record an adjusting payment or credit entry.",
        )

    await db.delete(tx)
    await db.commit()
    return None
