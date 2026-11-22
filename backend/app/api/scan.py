import io
import base64
import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.vision_service import (
    preprocess_image,
    extract_ledger_with_gemini,
    heuristic_sample_extractor,
    match_customers_in_db,
    find_best_matching_customer,
    transliterate_to_latin,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ScanAnalyzeRequest(BaseModel):
    image_base64: Optional[str] = None
    shop_id: Optional[int] = 1


class ScanEntryItem(BaseModel):
    temp_id: Optional[str] = None
    customer_name: str
    extracted_name: Optional[str] = None
    matched_customer_id: Optional[int] = None
    matched_customer_name: Optional[str] = None
    is_new_customer: bool = False
    amount: float
    type: str = "CREDIT"
    notes: Optional[str] = None
    date: Optional[str] = None


class ScanConfirmRequest(BaseModel):
    shop_id: Optional[int] = 1
    entries: List[ScanEntryItem]


async def recalculate_customer_balance(customer: Customer, db: AsyncSession) -> Decimal:
    """Calculate exact chronological running balance for customer from confirmed transactions."""
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
    return running_bal


@router.post("/analyze")
async def analyze_khata_photo(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    shop_id: int = Form(default=settings.SHOP_ID),
    db: AsyncSession = Depends(get_db),
):
    """
    Extracts customer ledger entries from a photo of a Khata book / receipt / notebook.
    Matches extracted names against existing customer profiles in the database.
    """
    image_bytes = None

    if file and file.filename:
        image_bytes = await file.read()
    elif image_base64:
        raw_b64 = image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(raw_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="No photograph provided. Please upload or capture an image.")

    try:
        pil_image = preprocess_image(image_bytes)
    except Exception as e:
        logger.error("Failed to decode image: %s", e)
        raise HTTPException(status_code=400, detail="Could not process image file. Please provide a valid photo.")

    # 1. Attempt extraction via Gemini Vision (gemini-3.5-flash / gemini-3.8-flash)
    entries = await extract_ledger_with_gemini(pil_image)

    # 2. If Gemini API was completely unreachable or returned an error (entries is None)
    if entries is None:
        logger.info("Gemini vision unavailable or network error. Using fallback demo extractor.")
        entries = heuristic_sample_extractor(image_bytes)

    # 3. Match against existing customer profiles in database
    enriched = await match_customers_in_db(entries, db, shop_id=shop_id)

    return {
        "success": True,
        "entry_count": len(enriched),
        "entries": enriched,
    }


@router.post("/confirm")
async def confirm_scanned_entries(
    payload: ScanConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Saves approved ledger entries into the database.
    - If customer exists in DB: adds transaction to that account and updates running balance.
    - If customer is new: creates a new account for that person and updates running balance.
    """
    if not payload.entries:
        raise HTTPException(status_code=400, detail="No entries to save.")

    shop_id = payload.shop_id or settings.SHOP_ID
    now = datetime.now(timezone.utc)

    # Load all existing active customers for lookup
    cust_res = await db.execute(
        select(Customer).where(Customer.shop_id == shop_id, Customer.is_active == True)
    )
    existing_customers = {c.id: c for c in cust_res.scalars().all()}
    name_to_customer = {c.name.strip().lower(): c for c in existing_customers.values()}

    new_customers_created = 0
    existing_customers_updated = 0
    saved_transactions = []

    for item in payload.entries:
        cust = None
        amount = Decimal(str(round(item.amount, 2)))
        tx_type = item.type.upper()
        if tx_type not in ("CREDIT", "PAYMENT"):
            tx_type = "CREDIT"

        # 1. Match by ID if provided
        if item.matched_customer_id and item.matched_customer_id in existing_customers:
            cust = existing_customers[item.matched_customer_id]
        else:
            # Check by exact name or transliteration to strictly avoid duplicate account creation
            matched_c, _ = find_best_matching_customer(item.customer_name, list(existing_customers.values()))
            if matched_c:
                cust = matched_c

        # 2. If customer profile exists -> use existing profile
        if cust:
            existing_customers_updated += 1
        else:
            # 3. New customer -> create profile
            new_cust_name = item.customer_name.strip() if item.customer_name.strip() else "New Customer"
            cust = Customer(
                shop_id=shop_id,
                name=new_cust_name,
                notes=f"Auto-created from Scan Book on {now.strftime('%d %b %Y')}",
                outstanding_balance=Decimal("0.00"),
                is_active=True,
            )
            db.add(cust)
            await db.flush()
            existing_customers[cust.id] = cust
            name_to_customer[cust.name.strip().lower()] = cust
            new_customers_created += 1

        # 4. Create confirmed transaction
        desc = item.notes or f"Khata entry from Scanned Book ({item.date or 'Today'})"
        tx = Transaction(
            shop_id=shop_id,
            customer_id=cust.id,
            type=tx_type,
            amount=amount,
            description=desc,
            voice_transcript=f"[Scan Book] {cust.name}: {tx_type} ₹{float(amount):,.0f}",
            status="CONFIRMED",
            created_at=now,
            confirmed_at=now,
        )
        db.add(tx)
        await db.flush()

        # 5. Recalculate customer's running balance
        await recalculate_customer_balance(cust, db)

        saved_transactions.append({
            "transaction_id": tx.id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "amount": float(amount),
            "type": tx_type,
            "new_balance": float(cust.outstanding_balance),
        })

    await db.commit()

    return {
        "success": True,
        "processed_count": len(payload.entries),
        "new_customers_created": new_customers_created,
        "existing_customers_updated": existing_customers_updated,
        "transactions": saved_transactions,
    }
