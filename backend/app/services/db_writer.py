import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, delete, desc
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionDraft
from app.models.promise import PaymentPromise
from app.services.llm_service import extract_promise_date
from app.core.database import AsyncSessionLocal
from app.services.voice_pipeline import PipelineProcessor, PipelineContext

logger = logging.getLogger(__name__)


class DatabaseWriteProcessor(PipelineProcessor):
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.error:
            return ctx

        if not ctx.nlu_result:
            return ctx

        intent = ctx.nlu_result.intent.value if hasattr(ctx.nlu_result.intent, "value") else str(ctx.nlu_result.intent)

        # 1. Handle CANCEL
        if intent == "CANCEL":
            async with AsyncSessionLocal() as db:
                await db.execute(
                    delete(TransactionDraft).where(TransactionDraft.session_id == ctx.session_id)
                )
                await db.commit()

            ctx.pipeline_state = "DONE"
            if ctx.language == "kn":
                ctx.response_text = "ವಹಿವಾಟು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ."
            elif ctx.language == "hi":
                ctx.response_text = "Transaction radd kar diya gaya hai."
            else:
                ctx.response_text = "Transaction cancelled."
            ctx.skip_to_tts = True
            return ctx

        # 2. Handle QUERY_BALANCE
        if intent == "QUERY_BALANCE":
            if ctx.confirmed_customer_id:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Customer).where(Customer.id == ctx.confirmed_customer_id)
                    )
                    cust = result.scalar_one_or_none()
                    if cust:
                        balance = float(cust.outstanding_balance)
                        ctx.new_balance = balance
                        ctx.confirmed_customer_name = cust.name
                        if ctx.language == "kn":
                            ctx.response_text = f"{cust.name} ಅವರ ಪ್ರಸ್ತುತ ಬಾಕಿ ₹{balance:,.0f}."
                        elif ctx.language == "hi":
                            ctx.response_text = f"{cust.name} ka baaki balance ₹{balance:,.0f} hai."
                        else:
                            ctx.response_text = f"The current balance for {cust.name} is ₹{balance:,.0f}."
                    else:
                        ctx.response_text = "Customer not found."
            else:
                ctx.response_text = "Which customer would you like to check the balance for?"

            ctx.pipeline_state = "DONE"
            ctx.skip_to_tts = True
            return ctx

        # 3. Handle QUERY_HISTORY
        if intent == "QUERY_HISTORY":
            if ctx.confirmed_customer_id:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Transaction)
                        .where(
                            Transaction.customer_id == ctx.confirmed_customer_id,
                            Transaction.status == "CONFIRMED"
                        )
                        .order_by(desc(Transaction.created_at))
                        .limit(3)
                    )
                    txs = result.scalars().all()
                    cust_res = await db.execute(
                        select(Customer).where(Customer.id == ctx.confirmed_customer_id)
                    )
                    cust = cust_res.scalar_one_or_none()
                    cust_name = cust.name if cust else ctx.confirmed_customer_name or "Customer"

                    if txs:
                        items = [f"₹{float(t.amount):,.0f} {t.type.lower()}" for t in txs]
                        tx_summary = ", ".join(items)
                        bal = float(cust.outstanding_balance) if cust else 0.0
                        if ctx.language == "kn":
                            ctx.response_text = f"{cust_name} ಅವರ ಇತ್ತೀಚಿನ ವಹಿವಾಟುಗಳು: {tx_summary}. ಒಟ್ಟು ಬಾಕಿ ₹{bal:,.0f}."
                        elif ctx.language == "hi":
                            ctx.response_text = f"{cust_name} ke pichle transactions: {tx_summary}. Kul baaki ₹{bal:,.0f} hai."
                        else:
                            ctx.response_text = f"Recent transactions for {cust_name}: {tx_summary}. Current balance is ₹{bal:,.0f}."
                    else:
                        ctx.response_text = f"No previous transactions found for {cust_name}."
            else:
                ctx.response_text = "Which customer's transaction history would you like to see?"

            ctx.pipeline_state = "DONE"
            ctx.skip_to_tts = True
            return ctx

        # 4. Handle RECORD_PROMISE
        if intent == "RECORD_PROMISE":
            async with AsyncSessionLocal() as db:
                customer_id = ctx.confirmed_customer_id
                customer = None

                if customer_id:
                    c_res = await db.execute(select(Customer).where(Customer.id == customer_id))
                    customer = c_res.scalar_one_or_none()

                if not customer:
                    name_to_find = (
                        ctx.confirmed_customer_name
                        or (ctx.nlu_result.customer_name if ctx.nlu_result else None)
                    )
                    if name_to_find:
                        c_res = await db.execute(
                            select(Customer).where(
                                Customer.shop_id == ctx.shop_id,
                                Customer.name.ilike(name_to_find.strip())
                            )
                        )
                        customer = c_res.scalar_one_or_none()

                if not customer:
                    # Auto-create customer if doesn't exist
                    new_name = (
                        ctx.confirmed_customer_name
                        or (ctx.nlu_result.customer_name if ctx.nlu_result else None)
                        or "Customer"
                    )
                    customer = Customer(
                        shop_id=ctx.shop_id,
                        name=new_name.strip(),
                        outstanding_balance=Decimal("0.00"),
                        is_active=True,
                    )
                    db.add(customer)
                    await db.flush()

                amount = float(ctx.nlu_result.amount) if (ctx.nlu_result and ctx.nlu_result.amount) else 0.0
                disp_date, iso_due_date = extract_promise_date(ctx.transcript or "")
                if ctx.nlu_result and ctx.nlu_result.promised_date:
                    disp_date = ctx.nlu_result.promised_date

                # Update customer's promised amount and promised date
                customer.promised_amount = Decimal(str(amount))
                customer.promised_date = disp_date
                customer.promise_notes = f"Promised ₹{amount:,.0f} on {disp_date}"

                # Insert row into payment_promises
                promise = PaymentPromise(
                    shop_id=ctx.shop_id,
                    customer_id=customer.id,
                    amount=Decimal(str(amount)),
                    promise_date=disp_date,
                    due_date=iso_due_date,
                    status="PENDING",
                    voice_transcript=ctx.transcript,
                )
                db.add(promise)
                await db.commit()
                await db.refresh(customer)
                await db.refresh(promise)

                ctx.confirmed_customer_id = customer.id
                ctx.confirmed_customer_name = customer.name
                ctx.new_balance = float(customer.outstanding_balance)
                setattr(ctx, "promised_amount", amount)
                setattr(ctx, "promised_date", disp_date)
                ctx.pipeline_state = "DONE"

                if ctx.language == "kn":
                    ctx.response_text = f"ಗುರುತು ಮಾಡಲಾಗಿದೆ! {customer.name} ಅವರು {disp_date} ರಂದು ₹{amount:,.0f} ಕೊಡುವುದಾಗಿ ಭರವಸೆ ನೀಡಿದ್ದಾರೆ. ಆ ದಿನ ನಿಮಗೆ ಜ್ಞಾಪಿಸಲಾಗುವುದು."
                elif ctx.language == "hi":
                    ctx.response_text = f"नोट कर लिया गया! {customer.name} ने {disp_date} को ₹{amount:,.0f} देने का वादा किया है। उस तारीख पर आपको याद दिलाया जाएगा।"
                else:
                    ctx.response_text = f"Noted! Recorded promise: {customer.name} will deposit ₹{amount:,.0f} on {disp_date}. You will be reminded on that date."

                ctx.skip_to_tts = True
                return ctx

        # 4b. Handle FULFILL_PROMISE
        if intent == "FULFILL_PROMISE":
            async with AsyncSessionLocal() as db:
                customer_id = ctx.confirmed_customer_id
                customer = None

                if customer_id:
                    c_res = await db.execute(select(Customer).where(Customer.id == customer_id))
                    customer = c_res.scalar_one_or_none()

                if not customer:
                    name_to_find = (
                        ctx.confirmed_customer_name
                        or (ctx.nlu_result.customer_name if ctx.nlu_result else None)
                    )
                    if name_to_find:
                        c_res = await db.execute(
                            select(Customer).where(
                                Customer.shop_id == ctx.shop_id,
                                Customer.name.ilike(name_to_find.strip())
                            )
                        )
                        customer = c_res.scalar_one_or_none()

                if not customer:
                    ctx.pipeline_state = "DONE"
                    if ctx.language == "kn":
                        ctx.response_text = "ಗ್ರಾಹಕರು ಕಂಡುಬಂದಿಲ್ಲ. ಭರವಸೆ ಪೂರ್ಣಗೊಳಿಸಲು ಗ್ರಾಹಕರ ಹೆಸರನ್ನು ತಿಳಿಸಿ."
                    elif ctx.language == "hi":
                        ctx.response_text = "ग्राहक नहीं मिला। वादा पूरा करने के लिए कृपया ग्राहक का नाम बताएं।"
                    else:
                        ctx.response_text = "Customer not found. Please specify which customer's promise to fulfill."
                    ctx.skip_to_tts = True
                    return ctx

                # Query pending promises for this customer
                p_res = await db.execute(
                    select(PaymentPromise)
                    .where(
                        PaymentPromise.shop_id == ctx.shop_id,
                        PaymentPromise.customer_id == customer.id,
                        PaymentPromise.status == "PENDING"
                    )
                    .order_by(PaymentPromise.id.asc())
                )
                pending_promises = p_res.scalars().all()

                if not pending_promises:
                    ctx.pipeline_state = "DONE"
                    ctx.confirmed_customer_id = customer.id
                    ctx.confirmed_customer_name = customer.name
                    if ctx.language == "kn":
                        ctx.response_text = f"{customer.name} ಅವರಿಗೆ ಯಾವುದೇ ಬಾಕಿ ಭರವಸೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ."
                    elif ctx.language == "hi":
                        ctx.response_text = f"{customer.name} के लिए कोई लंबित वादा नहीं मिला।"
                    else:
                        ctx.response_text = f"No pending payment promises found for {customer.name}."
                    ctx.skip_to_tts = True
                    return ctx

                # Match amount if given, else take earliest pending promise
                target_promise = None
                specified_amount = ctx.nlu_result.amount if (ctx.nlu_result and ctx.nlu_result.amount) else None
                if specified_amount:
                    for p in pending_promises:
                        if float(p.amount) == float(specified_amount):
                            target_promise = p
                            break
                if not target_promise:
                    target_promise = pending_promises[0]

                target_promise.status = "FULFILLED"

                # Check remaining pending promises for this customer
                remaining = [p for p in pending_promises if p.id != target_promise.id]
                if remaining:
                    next_p = remaining[0]
                    customer.promised_amount = next_p.amount
                    customer.promised_date = next_p.promise_date
                    customer.promise_notes = f"Promised ₹{float(next_p.amount):,.0f} on {next_p.promise_date}"
                else:
                    customer.promised_amount = Decimal("0.00")
                    customer.promised_date = None
                    customer.promise_notes = None

                await db.commit()
                await db.refresh(customer)
                await db.refresh(target_promise)

                prom_amount = float(target_promise.amount)
                ctx.confirmed_customer_id = customer.id
                ctx.confirmed_customer_name = customer.name
                ctx.new_balance = float(customer.outstanding_balance)
                setattr(ctx, "promised_amount", prom_amount)
                ctx.pipeline_state = "DONE"

                if ctx.language == "kn":
                    ctx.response_text = f"{customer.name} ಅವರ ₹{prom_amount:,.0f} ಪಾವತಿ ಭರವಸೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಾಗಿದೆ (Fulfilled)!"
                elif ctx.language == "hi":
                    ctx.response_text = f"{customer.name} का ₹{prom_amount:,.0f} का वादा पूरा (Fulfilled) दर्ज कर लिया गया है!"
                else:
                    ctx.response_text = f"Payment promise of ₹{prom_amount:,.0f} for {customer.name} has been marked as fulfilled!"

                ctx.skip_to_tts = True
                return ctx

        # 5. Handle QUERY_REMINDERS
        if intent == "QUERY_REMINDERS":
            async with AsyncSessionLocal() as db:
                today_iso = datetime.now().strftime("%Y-%m-%d")
                today_disp = datetime.now().strftime("%d %b %Y").lower()

                # Query pending promises due today or earlier
                p_res = await db.execute(
                    select(PaymentPromise, Customer)
                    .join(Customer, PaymentPromise.customer_id == Customer.id)
                    .where(
                        PaymentPromise.shop_id == ctx.shop_id,
                        PaymentPromise.status == "PENDING"
                    )
                    .order_by(PaymentPromise.id.desc())
                )
                rows = p_res.all()

                due_today = []
                for prom, cust in rows:
                    is_today = False
                    if prom.due_date and prom.due_date <= today_iso:
                        is_today = True
                    elif prom.promise_date and (today_disp in prom.promise_date.lower() or "today" in prom.promise_date.lower() or "aaj" in prom.promise_date.lower()):
                        is_today = True
                    if is_today:
                        due_today.append((prom, cust))

                ctx.pipeline_state = "DONE"
                if due_today:
                    parts = [f"{c.name}: ₹{float(p.amount):,.0f}" for p, c in due_today]
                    summary = ", ".join(parts)
                    count = len(due_today)
                    if ctx.language == "kn":
                        ctx.response_text = f"ಇಂದು {count} ಗ್ರಾಹಕರ ಪಾವತಿ ಜ್ಞಾಪನೆಗಳಿವೆ: {summary}."
                    elif ctx.language == "hi":
                        ctx.response_text = f"आज {count} ग्राहकों से पेमेंट आना है: {summary}।"
                    else:
                        ctx.response_text = f"Today's payment reminders ({count}): {summary}."
                else:
                    if ctx.language == "kn":
                        ctx.response_text = "ಇಂದು ಯಾವುದೇ ಪಾವತಿ ಬಾಕಿ ಭರವಸೆಗಳಿಲ್ಲ."
                    elif ctx.language == "hi":
                        ctx.response_text = "आज किसी भी ग्राहक का वादा किया हुआ पेमेंट देय नहीं है।"
                    else:
                        ctx.response_text = "No payment promises are due today."

                ctx.skip_to_tts = True
                return ctx

        # 6. Handle CONFIRM
        if intent == "CONFIRM":
            async with AsyncSessionLocal() as db:
                # Retrieve pending draft for session
                draft_res = await db.execute(
                    select(TransactionDraft).where(TransactionDraft.session_id == ctx.session_id)
                )
                draft = draft_res.scalar_one_or_none()

                customer_id = ctx.confirmed_customer_id or (draft.resolved_customer_id if draft else None)
                customer = None

                if not customer_id:
                    name_to_find = (
                        ctx.confirmed_customer_name
                        or (ctx.nlu_result.customer_name if ctx.nlu_result else None)
                        or (draft.extracted_customer_name if draft else None)
                    )
                    if name_to_find:
                        c_res = await db.execute(
                            select(Customer).where(
                                Customer.shop_id == ctx.shop_id,
                                Customer.name.ilike(name_to_find.strip())
                            )
                        )
                        cust = c_res.scalar_one_or_none()
                        if not cust:
                            cust = Customer(
                                shop_id=ctx.shop_id,
                                name=name_to_find.strip(),
                                outstanding_balance=Decimal("0.00"),
                                is_active=True,
                            )
                            db.add(cust)
                            await db.flush()
                        customer_id = cust.id
                        customer = cust

                amount = (
                    ctx.nlu_result.amount
                    if (ctx.nlu_result and ctx.nlu_result.amount)
                    else (float(draft.extracted_amount) if (draft and draft.extracted_amount) else None)
                )
                tx_type = (
                    ctx.nlu_result.transaction_type
                    if (ctx.nlu_result and ctx.nlu_result.transaction_type)
                    else (draft.extracted_type if (draft and draft.extracted_type) else "CREDIT")
                )
                transcript = (draft.raw_transcript if draft else None) or ctx.transcript

                if not customer_id or not amount:
                    ctx.pipeline_state = "DONE"
                    ctx.response_text = "No pending transaction found to confirm. What would you like to record?"
                    return ctx

                # Fetch customer if not already fetched
                if not customer:
                    cust_res = await db.execute(select(Customer).where(Customer.id == customer_id))
                    customer = cust_res.scalar_one_or_none()
                if not customer:
                    # If customer not found, create a new one automatically
                    new_name = (
                        (draft.extracted_customer_name if draft else None)
                        or (ctx.nlu_result.customer_name if ctx.nlu_result else None)
                        or ctx.confirmed_customer_name
                        or "Customer"
                    )
                    customer = Customer(
                        shop_id=ctx.shop_id,
                        name=new_name.strip(),
                        outstanding_balance=Decimal("0.00"),
                        is_active=True,
                    )
                    db.add(customer)
                    await db.flush()
                    logger.info("Auto-created missing customer '%s' (id=%s) during confirmation", customer.name, customer.id)

                # Create confirmed transaction
                now = datetime.now(timezone.utc)
                tx = Transaction(
                    shop_id=ctx.shop_id,
                    customer_id=customer.id,
                    type=tx_type,
                    amount=Decimal(str(amount)),
                    voice_transcript=transcript,
                    status="CONFIRMED",
                    session_id=ctx.session_id,
                    created_at=now,
                    confirmed_at=now,
                )
                db.add(tx)

                # Update customer balance
                current_bal = float(customer.outstanding_balance)
                if tx_type == "CREDIT":
                    new_bal = current_bal + amount
                else:  # PAYMENT
                    new_bal = max(0.0, current_bal - amount)

                    # Auto-fulfill pending promise for this customer if payment covers it
                    p_res = await db.execute(
                        select(PaymentPromise)
                        .where(
                            PaymentPromise.shop_id == ctx.shop_id,
                            PaymentPromise.customer_id == customer.id,
                            PaymentPromise.status == "PENDING"
                        )
                        .order_by(PaymentPromise.id.asc())
                    )
                    pending_promises = p_res.scalars().all()
                    for p in pending_promises:
                        if amount >= float(p.amount):
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

                # Delete draft
                if draft:
                    await db.delete(draft)

                await db.commit()
                await db.refresh(tx)
                await db.refresh(customer)

                ctx.transaction_id = tx.id
                ctx.new_balance = float(customer.outstanding_balance)
                ctx.confirmed_customer_id = customer.id
                ctx.confirmed_customer_name = customer.name
                ctx.pipeline_state = "DONE"

                if ctx.language == "kn":
                    ctx.response_text = f"ಖಾತೆ ಯಶಸ್ವಿಯಾಗಿ ನವೀಕರಿಸಲಾಗಿದೆ. {customer.name} ಅವರ ಹೊಸ ಬಾಕಿ ₹{ctx.new_balance:,.0f}."
                elif ctx.language == "hi":
                    ctx.response_text = f"खाता सफलतापूर्वक अपडेट हो गया है। {customer.name} का नया बकाया ₹{ctx.new_balance:,.0f} है।"
                else:
                    ctx.response_text = f"Transaction confirmed! New balance for {customer.name} is ₹{ctx.new_balance:,.0f}."

        return ctx
