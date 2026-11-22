from app.services.voice_pipeline import PipelineProcessor, PipelineContext


class TransactionValidatorProcessor(PipelineProcessor):
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.skip_to_tts or ctx.error:
            return ctx

        # If already set to CONFIRMING (e.g., customer ambiguous or not found), don't overwrite
        if ctx.pipeline_state == "CONFIRMING":
            return ctx

        if not ctx.nlu_result:
            return ctx

        intent = ctx.nlu_result.intent.value if hasattr(ctx.nlu_result.intent, "value") else str(ctx.nlu_result.intent)

        # Skip non-record intents
        if intent not in ("RECORD_CREDIT", "RECORD_PAYMENT"):
            return ctx

        # Check customer presence
        if not ctx.confirmed_customer_id or not ctx.confirmed_customer_name:
            ctx.pipeline_state = "CONFIRMING"
            ctx.response_text = "Which customer should I record this for?"
            return ctx

        # Check amount validity
        amount = ctx.nlu_result.amount
        if not amount or amount <= 0:
            ctx.pipeline_state = "CONFIRMING"
            ctx.response_text = f"How much amount should I record for {ctx.confirmed_customer_name}?"
            return ctx

        # Build confirmation message
        tx_type_str = "credit" if intent == "RECORD_CREDIT" else "payment"
        if ctx.language == "kn":
            if intent == "RECORD_CREDIT":
                ctx.response_text = f"{ctx.confirmed_customer_name} ಅವರಿಗೆ ₹{amount:,.0f} ಸಾಲ (ಕ್ರೆಡಿಟ್) ದಾಖಲಿಸಬೇಕೇ? ದೃಢೀಕರಿಸಲು 'ಸರಿ' ಅಥವಾ 'ಹೌದು' ಎನ್ನಿ."
            else:
                ctx.response_text = f"{ctx.confirmed_customer_name} ಅವರಿಂದ ₹{amount:,.0f} ಪಾವತಿ ದಾಖಲಿಸಬೇಕೇ? ದೃಢೀಕರಿಸಲು 'ಸರಿ' ಅಥವಾ 'ಹೌದು' ಎನ್ನಿ."
        elif ctx.language == "hi":
            if intent == "RECORD_CREDIT":
                ctx.response_text = f"{ctx.confirmed_customer_name} के लिए ₹{amount:,.0f} उधार दर्ज करें? पुष्टि करने के लिए 'हाँ' कहें।"
            else:
                ctx.response_text = f"{ctx.confirmed_customer_name} से ₹{amount:,.0f} जमा (भुगतान) दर्ज करें? पुष्टि करने के लिए 'हाँ' कहें।"
        else:
            ctx.response_text = f"Record ₹{amount:,.0f} {tx_type_str} for {ctx.confirmed_customer_name}? Say yes to confirm or change."

        ctx.pipeline_state = "CONFIRMING"
        return ctx
