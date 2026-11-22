import logging
from rapidfuzz import fuzz
from sqlalchemy import select
from app.models.customer import Customer
from app.services.voice_pipeline import PipelineProcessor, PipelineContext
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

DEVANAGARI_MAP = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'अ': 'a', 'आ': 'a', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n', '्': ''
}

KANNADA_MAP = {
    'ಕ': 'k', 'ಖ': 'kh', 'ಗ': 'g', 'ಘ': 'gh', 'ಙ': 'n',
    'ಚ': 'ch', 'ಛ': 'chh', 'ಜ': 'j', 'ಝ': 'jh', 'ಞ': 'n',
    'ಟ': 't', 'ಠ': 'th', 'ಡ': 'd', 'ಢ': 'dh', 'ಣ': 'n',
    'ತ': 't', 'ಥ': 'th', 'ದ': 'd', 'ಧ': 'dh', 'ನ': 'n',
    'ಪ': 'p', 'ಫ': 'ph', 'ಬ': 'b', 'ಭ': 'bh', 'ಮ': 'm',
    'ಯ': 'y', 'ರ': 'r', 'ಲ': 'l', 'ವ': 'v', 'ಶ': 'sh', 'ಷ': 'sh', 'ಸ': 's', 'ಹ': 'h', 'ಳ': 'l',
    'ಅ': 'a', 'ಆ': 'a', 'ಇ': 'i', 'ಈ': 'ee', 'ಉ': 'u', 'ಊ': 'oo', 'ಋ': 'ri',
    'ಎ': 'e', 'ಏ': 'ee', 'ಐ': 'ai', 'ಒ': 'o', 'ಓ': 'oo', 'ಔ': 'au',
    'ಾ': 'a', 'ಿ': 'i', 'ೀ': 'ee', 'ು': 'u', 'ೂ': 'oo', 'ೃ': 'ri',
    'ೆ': 'e', 'ೇ': 'ee', 'ೈ': 'ai', 'ೊ': 'o', 'ೋ': 'oo', 'ೌ': 'au', 'ಂ': 'm', '್': ''
}

def to_latin_simple(text: str) -> str:
    if not text:
        return ""
    res = []
    for ch in text:
        if ch in DEVANAGARI_MAP:
            res.append(DEVANAGARI_MAP[ch])
        elif ch in KANNADA_MAP:
            res.append(KANNADA_MAP[ch])
        else:
            res.append(ch)
    return "".join(res).strip().lower()


class CustomerResolverService:
    async def resolve_or_create(self, name: str, shop_id: int, context_text: str = "") -> dict:
        clean_name = name.strip()
        latin_name = to_latin_simple(clean_name)
        spoken_words = clean_name.lower().split()
        spoken_latin_words = latin_name.split() if latin_name else []
        spoken_first_latin = spoken_latin_words[0] if spoken_latin_words else ""

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Customer).where(
                    Customer.shop_id == shop_id,
                    Customer.is_active == True
                )
            )
            customers = result.scalars().all()

            if customers:
                # Stage 1: Exact matches (in original script or transliterated)
                exact = [
                    c for c in customers
                    if c.name.lower() == clean_name.lower()
                    or (latin_name and to_latin_simple(c.name) == latin_name)
                ]
                if len(exact) == 1:
                    logger.info("Exact customer match: %s -> %s", clean_name, exact[0].name)
                    return {"status": "RESOLVED", "customer": exact[0]}
                if len(exact) > 1:
                    return self._try_landmark_then_disambiguate(exact, context_text)

                # Stage 2: Single-word / First-name match (e.g. "Suresh" matching "Suresh Patel")
                if len(spoken_latin_words) == 1 and spoken_first_latin:
                    first_matches = []
                    for c in customers:
                        c_latin_words = to_latin_simple(c.name).split()
                        c_first = c_latin_words[0] if c_latin_words else ""
                        if c_first == spoken_first_latin or (c.alias and spoken_first_latin in to_latin_simple(c.alias)):
                            first_matches.append(c)

                    if len(first_matches) == 1:
                        logger.info("First-name match: %s -> %s", clean_name, first_matches[0].name)
                        return {"status": "RESOLVED", "customer": first_matches[0]}
                    elif len(first_matches) > 1:
                        res = self._try_landmark_then_disambiguate(first_matches, context_text)
                        if res["status"] == "RESOLVED":
                            return res

                # Stage 3: High-confidence fuzzy match (first name must match or high similarity)
                best_match = None
                best_score = 0
                for c in customers:
                    c_latin = to_latin_simple(c.name)
                    c_words = c_latin.split()
                    c_first = c_words[0] if c_words else ""

                    score = fuzz.ratio(latin_name, c_latin)
                    first_ratio = fuzz.ratio(spoken_first_latin, c_first) if spoken_first_latin and c_first else 0

                    # Must have same first name or overall ratio >= 88
                    if (first_ratio >= 80 and score >= 80) or score >= 88:
                        if score > best_score:
                            best_score = score
                            best_match = c

                if best_match:
                    logger.info("High-confidence fuzzy match: %s -> %s (score: %s)", clean_name, best_match.name, best_score)
                    return {"status": "RESOLVED", "customer": best_match}

            # Stage 4: NO MATCH FOUND -> Automatically create new customer!
            logger.info("No existing customer found for '%s'. Automatically creating new customer in shop %s.", clean_name, shop_id)
            new_customer = Customer(
                shop_id=shop_id,
                name=clean_name,
                outstanding_balance=0.00,
                is_active=True,
            )
            db.add(new_customer)
            await db.commit()
            await db.refresh(new_customer)
            logger.info("Created new customer '%s' with id=%s", new_customer.name, new_customer.id)
            return {"status": "RESOLVED", "customer": new_customer, "created": True}

    def _try_landmark_then_disambiguate(self, customers, context_text: str):
        ctx_lower = context_text.lower()
        ctx_latin = to_latin_simple(context_text)
        for c in customers:
            if c.landmark:
                l_lower = c.landmark.lower()
                l_latin = to_latin_simple(c.landmark)
                if l_lower in ctx_lower or (l_latin and l_latin in ctx_latin):
                    return {"status": "RESOLVED", "customer": c}
            if c.alias:
                a_lower = c.alias.lower()
                a_latin = to_latin_simple(c.alias)
                if a_lower in ctx_lower or (a_latin and a_latin in ctx_latin):
                    return {"status": "RESOLVED", "customer": c}
        return self._disambiguate(customers)

    def _disambiguate(self, customers):
        options = []
        for c in customers:
            label = c.name
            if c.landmark:
                label += f" (near {c.landmark})"
            elif c.alias:
                label += f" ({c.alias})"
            options.append({"id": c.id, "name": c.name, "label": label})
        question = self._build_question(options)
        return {"status": "AMBIGUOUS", "customers": options, "disambiguation_question": question}

    def _build_question(self, options):
        labels = [f"'{o['label']}'" for o in options]
        if len(labels) == 2:
            return f"Which customer? {labels[0]} or {labels[1]}?"
        return f"I found multiple customers. Which one: {', '.join(labels[:-1])}, or {labels[-1]}?"


class CustomerResolverProcessor(PipelineProcessor):
    def __init__(self):
        self.service = CustomerResolverService()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.skip_to_tts or ctx.error:
            return ctx
        if not ctx.nlu_result:
            return ctx

        intent = ctx.nlu_result.intent.value if hasattr(ctx.nlu_result.intent, "value") else str(ctx.nlu_result.intent)

        # Only resolve for transaction or query intents
        if intent in ("CONFIRM", "CANCEL", "UNKNOWN"):
            return ctx

        if not ctx.nlu_result.customer_name:
            if intent in ("RECORD_CREDIT", "RECORD_PAYMENT"):
                ctx.pipeline_state = "CONFIRMING"
                if ctx.language == "hi":
                    ctx.response_text = "यह किस ग्राहक के खाते में दर्ज करना है?"
                elif ctx.language == "kn":
                    ctx.response_text = "ಯಾವ ಗ್ರಾಹಕರ ಖಾತೆಗೆ ದಾಖಲಿಸಬೇಕು?"
                else:
                    ctx.response_text = "Which customer should I record this for?"
            elif intent in ("QUERY_BALANCE", "QUERY_HISTORY"):
                ctx.pipeline_state = "CONFIRMING"
                if ctx.language == "hi":
                    ctx.response_text = "आप किस ग्राहक का बैलेंस देखना चाहते हैं?"
                elif ctx.language == "kn":
                    ctx.response_text = "ಯಾವ ಗ್ರಾಹಕರ ಬಾಕಿ ಪರಿಶೀಲಿಸಬೇಕು?"
                else:
                    ctx.response_text = "Which customer would you like to check?"
            elif intent == "FULFILL_PROMISE":
                ctx.pipeline_state = "CONFIRMING"
                if ctx.language == "hi":
                    ctx.response_text = "किस ग्राहक का वादा पूरा करना है?"
                elif ctx.language == "kn":
                    ctx.response_text = "ಯಾವ ಗ್ರಾಹಕರ ಭರವಸೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಬೇಕು?"
                else:
                    ctx.response_text = "Which customer's promise would you like to fulfill?"
            return ctx

        result = await self.service.resolve_or_create(
            name=ctx.nlu_result.customer_name,
            shop_id=ctx.shop_id,
            context_text=ctx.transcript or ""
        )

        if result["status"] == "RESOLVED":
            ctx.confirmed_customer_id = result["customer"].id
            ctx.confirmed_customer_name = result["customer"].name
        elif result["status"] == "AMBIGUOUS":
            ctx.pipeline_state = "CONFIRMING"
            ctx.response_text = result["disambiguation_question"]
            ctx.disambiguation_options = result["customers"]

        return ctx
