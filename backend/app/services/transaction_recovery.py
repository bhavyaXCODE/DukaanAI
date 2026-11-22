from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, delete
from app.models.transaction import TransactionDraft
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.services.voice_pipeline import PipelineProcessor, PipelineContext


class DraftRecoveryService:
    @staticmethod
    async def save_draft(ctx: PipelineContext) -> Optional[TransactionDraft]:
        async with AsyncSessionLocal() as db:
            # Check existing draft for this session
            stmt = select(TransactionDraft).where(TransactionDraft.session_id == ctx.session_id)
            result = await db.execute(stmt)
            draft = result.scalar_one_or_none()

            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.DRAFT_TTL_HOURS)
            tx_type = None
            if ctx.nlu_result:
                tx_type = ctx.nlu_result.transaction_type
                if not tx_type:
                    intent_str = str(ctx.nlu_result.intent)
                    if "CREDIT" in intent_str:
                        tx_type = "CREDIT"
                    elif "PAYMENT" in intent_str:
                        tx_type = "PAYMENT"

            amount = ctx.nlu_result.amount if ctx.nlu_result else None
            customer_name = ctx.confirmed_customer_name or (
                ctx.nlu_result.customer_name if ctx.nlu_result else None
            )

            if draft:
                # Update existing draft
                if ctx.transcript:
                    draft.raw_transcript = ctx.transcript
                if customer_name:
                    draft.extracted_customer_name = customer_name
                if ctx.confirmed_customer_id:
                    draft.resolved_customer_id = ctx.confirmed_customer_id
                if amount is not None:
                    draft.extracted_amount = amount
                if tx_type:
                    draft.extracted_type = tx_type
                draft.ambiguity_flag = bool(ctx.disambiguation_options)
                draft.ambiguity_reason = ctx.response_text if ctx.disambiguation_options else None
                draft.conversation_history = ctx.conversation_history
                draft.expires_at = expires_at
            else:
                # Create new draft
                draft = TransactionDraft(
                    session_id=ctx.session_id,
                    shop_id=ctx.shop_id,
                    raw_transcript=ctx.transcript,
                    extracted_customer_name=customer_name,
                    resolved_customer_id=ctx.confirmed_customer_id,
                    extracted_amount=amount,
                    extracted_type=tx_type,
                    ambiguity_flag=bool(ctx.disambiguation_options),
                    ambiguity_reason=ctx.response_text if ctx.disambiguation_options else None,
                    conversation_history=ctx.conversation_history,
                    expires_at=expires_at,
                )
                db.add(draft)

            await db.commit()
            await db.refresh(draft)
            ctx.draft_id = draft.id
            return draft

    @staticmethod
    async def get_pending_draft(shop_id: int) -> Optional[TransactionDraft]:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            stmt = (
                select(TransactionDraft)
                .where(
                    TransactionDraft.shop_id == shop_id,
                    (TransactionDraft.expires_at == None) | (TransactionDraft.expires_at > now),
                )
                .order_by(TransactionDraft.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_draft_by_session(session_id: str) -> Optional[TransactionDraft]:
        async with AsyncSessionLocal() as db:
            stmt = select(TransactionDraft).where(TransactionDraft.session_id == session_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def cancel_draft(session_id: str) -> bool:
        async with AsyncSessionLocal() as db:
            stmt = delete(TransactionDraft).where(TransactionDraft.session_id == session_id)
            res = await db.execute(stmt)
            await db.commit()
            return (res.rowcount or 0) > 0

    @staticmethod
    def resume_draft(draft: TransactionDraft) -> dict:
        return {
            "session_id": draft.session_id,
            "customer_name": draft.extracted_customer_name,
            "resolved_customer_id": draft.resolved_customer_id,
            "amount": float(draft.extracted_amount) if draft.extracted_amount else None,
            "type": draft.extracted_type,
            "ambiguity_flag": draft.ambiguity_flag,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
        }


class DraftSaveProcessor(PipelineProcessor):
    def __init__(self):
        self.service = DraftRecoveryService()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.skip_to_tts or ctx.error:
            return ctx

        # Save draft if we are in confirming state
        if ctx.pipeline_state == "CONFIRMING":
            await self.service.save_draft(ctx)

        return ctx
