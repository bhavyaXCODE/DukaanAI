from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.core.config import settings
from app.models.promise import PaymentPromise
from app.models.customer import Customer
from pydantic import BaseModel

router = APIRouter()


class PromiseCreate(BaseModel):
    shop_id: Optional[int] = 1
    customer_id: int
    amount: float
    promise_date: str
    due_date: Optional[str] = None
    voice_transcript: Optional[str] = None


class PromiseResponse(BaseModel):
    id: int
    shop_id: int
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    customer_landmark: Optional[str] = None
    amount: float
    promise_date: str
    due_date: Optional[str] = None
    status: str
    voice_transcript: Optional[str] = None
    created_at: datetime
    is_due_today: bool = False


@router.get("/today", response_model=List[PromiseResponse])
async def get_today_promises(
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_disp = datetime.now().strftime("%d %b %Y").lower()

    result = await db.execute(
        select(PaymentPromise, Customer)
        .join(Customer, PaymentPromise.customer_id == Customer.id)
        .where(
            PaymentPromise.shop_id == shop_id,
            PaymentPromise.status == "PENDING"
        )
        .order_by(PaymentPromise.id.desc())
    )
    rows = result.all()

    today_items = []
    for prom, cust in rows:
        is_today = False
        if prom.due_date and prom.due_date <= today_iso:
            is_today = True
        elif prom.promise_date and (
            today_disp in prom.promise_date.lower()
            or "today" in prom.promise_date.lower()
            or "aaj" in prom.promise_date.lower()
            or "kal" in prom.promise_date.lower()
        ):
            is_today = True

        if is_today:
            today_items.append(
                PromiseResponse(
                    id=prom.id,
                    shop_id=prom.shop_id,
                    customer_id=cust.id,
                    customer_name=cust.name,
                    customer_phone=cust.phone,
                    customer_landmark=cust.landmark,
                    amount=float(prom.amount),
                    promise_date=prom.promise_date,
                    due_date=prom.due_date,
                    status=prom.status,
                    voice_transcript=prom.voice_transcript,
                    created_at=prom.created_at,
                    is_due_today=True,
                )
            )
    return today_items


@router.get("", response_model=List[PromiseResponse])
async def get_all_promises(
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    today_iso = datetime.now().strftime("%Y-%m-%d")
    result = await db.execute(
        select(PaymentPromise, Customer)
        .join(Customer, PaymentPromise.customer_id == Customer.id)
        .where(PaymentPromise.shop_id == shop_id)
        .order_by(PaymentPromise.id.desc())
    )
    rows = result.all()

    items = []
    for prom, cust in rows:
        is_today = bool(prom.due_date and prom.due_date <= today_iso and prom.status == "PENDING")
        items.append(
            PromiseResponse(
                id=prom.id,
                shop_id=prom.shop_id,
                customer_id=cust.id,
                customer_name=cust.name,
                customer_phone=cust.phone,
                customer_landmark=cust.landmark,
                amount=float(prom.amount),
                promise_date=prom.promise_date,
                due_date=prom.due_date,
                status=prom.status,
                voice_transcript=prom.voice_transcript,
                created_at=prom.created_at,
                is_due_today=is_today,
            )
        )
    return items


@router.post("", response_model=PromiseResponse)
async def create_promise(
    payload: PromiseCreate,
    db: AsyncSession = Depends(get_db),
):
    cust_res = await db.execute(select(Customer).where(Customer.id == payload.customer_id))
    cust = cust_res.scalar_one_or_none()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    new_promise = PaymentPromise(
        shop_id=payload.shop_id or 1,
        customer_id=payload.customer_id,
        amount=Decimal(str(payload.amount)),
        promise_date=payload.promise_date,
        due_date=payload.due_date,
        status="PENDING",
        voice_transcript=payload.voice_transcript,
    )
    db.add(new_promise)

    # Update customer record
    cust.promised_amount = Decimal(str(payload.amount))
    cust.promised_date = payload.promise_date
    cust.promise_notes = f"Promised ₹{payload.amount:,.0f} on {payload.promise_date}"

    await db.commit()
    await db.refresh(new_promise)
    await db.refresh(cust)

    today_iso = datetime.now().strftime("%Y-%m-%d")
    is_today = bool(new_promise.due_date and new_promise.due_date <= today_iso)

    return PromiseResponse(
        id=new_promise.id,
        shop_id=new_promise.shop_id,
        customer_id=cust.id,
        customer_name=cust.name,
        customer_phone=cust.phone,
        customer_landmark=cust.landmark,
        amount=float(new_promise.amount),
        promise_date=new_promise.promise_date,
        due_date=new_promise.due_date,
        status=new_promise.status,
        voice_transcript=new_promise.voice_transcript,
        created_at=new_promise.created_at,
        is_due_today=is_today,
    )


@router.post("/{promise_id}/fulfill")
async def fulfill_promise(
    promise_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PaymentPromise).where(PaymentPromise.id == promise_id))
    prom = result.scalar_one_or_none()
    if not prom:
        raise HTTPException(status_code=404, detail="Payment promise not found")

    prom.status = "FULFILLED"

    # Reset customer promised amount if it matches
    c_res = await db.execute(select(Customer).where(Customer.id == prom.customer_id))
    cust = c_res.scalar_one_or_none()
    if cust and cust.promised_amount and cust.promised_amount == prom.amount:
        cust.promised_amount = Decimal("0.00")
        cust.promised_date = None
        cust.promise_notes = None

    await db.commit()
    return {"success": True, "id": promise_id, "status": "FULFILLED"}


@router.post("/{promise_id}/dismiss")
async def dismiss_promise(
    promise_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PaymentPromise).where(PaymentPromise.id == promise_id))
    prom = result.scalar_one_or_none()
    if not prom:
        raise HTTPException(status_code=404, detail="Payment promise not found")

    prom.status = "DISMISSED"

    c_res = await db.execute(select(Customer).where(Customer.id == prom.customer_id))
    cust = c_res.scalar_one_or_none()
    if cust and cust.promised_amount and cust.promised_amount == prom.amount:
        cust.promised_amount = Decimal("0.00")
        cust.promised_date = None
        cust.promise_notes = None

    await db.commit()
    return {"success": True, "id": promise_id, "status": "DISMISSED"}
