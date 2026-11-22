from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, case
from rapidfuzz import fuzz
from app.core.database import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
)
from app.schemas.transaction import TransactionResponse, TransactionListResponse

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=500),
    search: Optional[str] = None,
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size
    query = select(Customer).where(Customer.shop_id == shop_id, Customer.is_active == True)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Customer.name.ilike(search_filter),
                Customer.alias.ilike(search_filter),
                Customer.landmark.ilike(search_filter),
                Customer.phone.ilike(search_filter),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paginated results ordered alphabetically (case-insensitive)
    query = query.order_by(func.lower(Customer.name).asc()).offset(offset).limit(size)
    result = await db.execute(query)
    customers = result.scalars().all()

    # Recalculate each customer's outstanding_balance, total_credit, and total_payments from confirmed transactions
    customer_responses = []
    for c in customers:
        tx_stmt = select(
            func.coalesce(func.sum(case((Transaction.type == "CREDIT", Transaction.amount), else_=0)), 0).label("tot_credit"),
            func.coalesce(func.sum(case((Transaction.type == "PAYMENT", Transaction.amount), else_=0)), 0).label("tot_payment"),
        ).where(Transaction.customer_id == c.id, Transaction.status == "CONFIRMED")
        tx_res = await db.execute(tx_stmt)
        tot_credit, tot_payment = tx_res.one()

        # Chronological running balance calculation:
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

        c.outstanding_balance = running_bal

        resp_item = CustomerResponse(
            id=c.id,
            shop_id=c.shop_id,
            name=c.name,
            alias=c.alias,
            phone=c.phone,
            landmark=c.landmark,
            notes=c.notes,
            outstanding_balance=float(running_bal),
            total_credit=float(tot_credit),
            total_payments=float(tot_payment),
            promised_amount=float(c.promised_amount or 0.0),
            promised_date=c.promised_date,
            promise_notes=c.promise_notes,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        customer_responses.append(resp_item)

    await db.commit()

    return CustomerListResponse(
        items=customer_responses,
        total=total,
        page=page,
        size=size,
    )


@router.get("/search", response_model=List[CustomerResponse])
async def search_customers(
    q: str = Query(..., min_length=1),
    shop_id: int = Query(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Customer).where(Customer.shop_id == shop_id, Customer.is_active == True)
    )
    all_customers = result.scalars().all()

    scored = []
    q_lower = q.lower()
    for c in all_customers:
        # Score against name, alias, landmark
        score_name = fuzz.WRatio(q_lower, c.name.lower())
        score_alias = fuzz.WRatio(q_lower, c.alias.lower()) if c.alias else 0
        score_landmark = fuzz.WRatio(q_lower, c.landmark.lower()) if c.landmark else 0
        max_score = max(score_name, score_alias, score_landmark)

        # Direct substring matching bonus
        if q_lower in c.name.lower() or (c.alias and q_lower in c.alias.lower()):
            max_score = max(max_score, 85)

        if max_score >= 60:
            scored.append((c, max_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [CustomerResponse.model_validate(c[0]) for c in scored[:10]]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    customer = Customer(
        shop_id=customer_in.shop_id or settings.SHOP_ID,
        name=customer_in.name.strip(),
        alias=customer_in.alias.strip() if customer_in.alias else None,
        phone=customer_in.phone.strip() if customer_in.phone else None,
        landmark=customer_in.landmark.strip() if customer_in.landmark else None,
        notes=customer_in.notes.strip() if customer_in.notes else None,
        outstanding_balance=Decimal(str(customer_in.outstanding_balance or 0.0)),
        is_active=True,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=dict)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Recalculate customer's balance, total_credit, total_payments from confirmed transactions
    tx_stmt = select(
        func.coalesce(func.sum(case((Transaction.type == "CREDIT", Transaction.amount), else_=0)), 0).label("tot_credit"),
        func.coalesce(func.sum(case((Transaction.type == "PAYMENT", Transaction.amount), else_=0)), 0).label("tot_payment"),
    ).where(Transaction.customer_id == customer.id, Transaction.status == "CONFIRMED")
    tx_res = await db.execute(tx_stmt)
    tot_credit, tot_payment = tx_res.one()

    tx_rows_stmt = select(Transaction.type, Transaction.amount).where(
        Transaction.customer_id == customer.id,
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

    customer.outstanding_balance = running_bal
    await db.commit()

    # Fetch 5 most recent transactions
    tx_res = await db.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(desc(Transaction.created_at))
        .limit(5)
    )
    transactions = tx_res.scalars().all()

    tx_items = []
    for t in transactions:
        tx_dict = TransactionResponse.model_validate(t).model_dump()
        tx_dict["customer_name"] = customer.name
        tx_items.append(tx_dict)

    cust_resp = CustomerResponse(
        id=customer.id,
        shop_id=customer.shop_id,
        name=customer.name,
        alias=customer.alias,
        phone=customer.phone,
        landmark=customer.landmark,
        notes=customer.notes,
        outstanding_balance=float(running_bal),
        total_credit=float(tot_credit),
        total_payments=float(tot_payment),
        promised_amount=float(customer.promised_amount or 0.0),
        promised_date=customer.promised_date,
        promise_notes=customer.promise_notes,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )
    cust_dict = cust_resp.model_dump()
    cust_dict["recent_transactions"] = tx_items
    return cust_dict


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "outstanding_balance" and value is not None:
            setattr(customer, field, Decimal(str(value)))
        else:
            setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}/transactions", response_model=TransactionListResponse)
async def get_customer_transactions(
    customer_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size

    # Ensure customer exists
    cust_res = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    query = select(Transaction).where(Transaction.customer_id == customer_id)

    count_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_res.scalar() or 0

    query = query.order_by(desc(Transaction.created_at)).offset(offset).limit(size)
    tx_result = await db.execute(query)
    transactions = tx_result.scalars().all()

    items = []
    for t in transactions:
        tx_data = TransactionResponse.model_validate(t)
        tx_data.customer_name = customer.name
        items.append(tx_data)

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )
