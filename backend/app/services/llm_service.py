import json
import re
import logging
import asyncio
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from app.core.config import settings
from app.schemas.voice import NLUResult, VoiceIntent
from app.services.voice_pipeline import PipelineProcessor, PipelineContext

logger = logging.getLogger(__name__)

# Configure Google Generative AI
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning("Failed to configure genai: %s", e)

SYSTEM_PROMPT = """You are DukaanAI, an intelligent voice accounting assistant for Indian kirana shopkeepers and small neighbourhood retailers.
Extract transaction intent, customer name, and amount from spoken voice commands in Kannada, Hindi, English, or code-mixed Indic languages.

CRITICAL FINANCIAL RULES:
1. Intent & Transaction Type:
- RECORD_CREDIT:
  * Customer owes shopkeeper money or bought goods on credit (उधार / ಸಾಲ).
  * Keywords: udhar, credit, liya, le gaya, took, saala, ಸಾಲ, ನೀಡಿದೆ, ಕ್ರೆಡಿಟ್, ಕಡ, उधार दिया, उधार, सामान लिया, खाते में डालो.
  * transaction_type MUST be "CREDIT".

- RECORD_PAYMENT:
  * Customer is paying money back / clearing dues / depositing cash or UPI (जमा / ಪಾವತಿ / चुकता).
  * Keywords: payment, paid, jama, waapas, received, diya, chukaye, vasooli, aagide, bantu, kotru, ಪಾವತಿ, ಜಮಾ, ಪಡೆದರು, ಹಣ ಕೊಟ್ಟರು, जमा प्राप्त, जमा हुआ, चुकाए, भुगतान, वापस दिया, पैसे दिए, हिसाब चुकता.
  * transaction_type MUST be "PAYMENT".

- RECORD_PROMISE:
  * Customer promises, commits, or agrees to pay/deposit money on a specific date or time in the future.
  * Keywords: promise, promised, will pay, will deposit, will give, dega, denge, degi, kal dega, parso dega, vaada, tareekh ko dega, nale kodthane, kodthare, ಭರವಸೆ, ಸಾಲ ತೀರಿಸುತ್ತೇನೆ, वादा किया, पैसे देगा, कल देगा, परसों देगा.
  * transaction_type MUST be "PROMISE".
  * promised_date: Extract date string (e.g. "25 Nov 2026", "Tomorrow", "Friday", "2026-11-25").

- FULFILL_PROMISE:
  * Customer has paid or fulfilled their promised deposit, or shopkeeper marks a promise as completed/fulfilled/cleared/paid.
  * Keywords:
    - English: "fulfill promise", "fulfilled promise", "promise fulfilled", "promise complete", "promise completed", "promise paid", "mark promise as fulfilled", "paid his promise", "promise done", "clear promise", "settled promise".
    - Hindi: "वादा पूरा हो गया", "प्रॉमिस पूरा हो गया", "वादा पूरा करो", "प्रॉमिस फुलफिल करो", "वादे का पैसा दे दिया", "प्रॉमिस पूरा कर दिया", "वादा चुकाया", "प्रॉमिस चुका दिया", "वादा पूरा".
    - Kannada: "ಭರವಸೆ ಪೂರ್ಣಗೊಂಡಿದೆ", "ಪ್ರಾಮಿಸ್ ಕಂಪ್ಲೀಟ್ ಆಗಿದೆ", "ಭರವಸೆ ಪೂರ್ಣಗೊಳಿಸಿ", "ಭರವಸೆ ತೀರಿಸಿದ್ದಾರೆ", "ಮಾತು ಉಳಿಸಿಕೊಂಡಿದ್ದಾರೆ", "ಭರವಸೆ ಮುಗಿದಿದೆ", "ಪ್ರಾಮಿಸ್ ಫುಲ್ಫಿಲ್ ಮಾಡಿ".
  * customer_name: Extract the customer's name (e.g. "Ramesh", "Govind").
  * amount: number_or_null (if specified in utterance).
  * transaction_type: "FULFILL_PROMISE".

- QUERY_REMINDERS:
  * Shopkeeper asking who has promised to pay today or asking for payment reminders/dues scheduled for today.
  * Keywords: reminders today, who has to pay, kiske paise aane hai, aaj kiska payment hai, aaj kiska vaada tha, ivatthu yaaru kodbeku, reminder, aaj ke promises.
  * transaction_type MUST be null.

- QUERY_BALANCE:
  * Shopkeeper asking for customer balance (kitna baaki hai, balance, outstanding, ಬಾಕಿ ಎಷ್ಟು).
  * transaction_type MUST be null.

- QUERY_HISTORY:
  * Asking for previous transactions / history (pichle hisaab, history, ವಹಿವಾಟು).
  * transaction_type MUST be null.

- CONFIRM:
  * Affirmation / confirmation (yes, haan, ha, sahi, sari, houdu, confirm, theek hai, हाँ, ಹೌದು, ಖಚಿತ).
  * transaction_type MUST be null.

- CANCEL:
  * Rejection / cancellation (no, nahi, beda, cancel, mat karo, मत करो, रद्द, ಬೇಡ, ಇಲ್ಲ).
  * transaction_type MUST be null.

2. Customer Name Identification (What IS a name vs NOT a name):
- Extract ONLY the actual person's name (e.g. "लक्ष्मी", "सुरेश कुमार", "रवि", "आनंद", "Suresh Patel", "Ramesh", "Govind").
- ALWAYS STRIP honorifics and relational suffixes:
  * Hindi: 'जी' (Ji), 'भैया' (Bhaiya), 'बाबू' (Babu), 'अंकल' (Uncle), 'सेठ' (Seth), 'सर' (Sir), 'मास्टर' (Master).
  * Kannada: 'ಅಣ್ಣ' (Anna), 'ಅವರು' (Avaru), 'ಮೇಷ್ಟ್ರು' (Meshtru), 'ಗೌಡ್ರು' (Gowdru).
  * English: 'Mr', 'Mrs', 'Master', 'Sir'.
- ALWAYS STRIP grammatical postpositions:
  * Hindi: 'को', 'का', 'के', 'की', 'से', 'ने', 'में', 'पर'.
  * Kannada: 'ಗೆ', 'ಇಂದ', 'ನಲ್ಲಿ'.
  * English: 'to', 'from', 'of', 'for'.
- NEVER extract grocery items, commodities, or nouns as customer names:
  * Examples of NOT names: 'चावल' (rice), 'आटा' (flour), 'तेल' (oil), 'दूध' (milk), 'शक्कर' (sugar), 'दाल' (dal), 'सिगरेट' (cigarette), 'साबुन' (soap).
- If NO human person is named (e.g. only "500 रुपये उधार" or "1000 payment"), customer_name MUST be null.

3. Spoken Amount Parsing:
- Extract numbers directly (e.g. ₹500, 250, 1000).
- Comma-formatted numbers: ALWAYS extract numbers formatted with commas as their full integer value (e.g. '15,000' = 15000, '1,50,000' = 150000, '5,000' = 5000). NEVER truncate '15,000' to 15!
- Verbal Indic numbers:
  * 'दो सौ पचास' = 250, 'पांच सौ' = 500, 'एक हजार' = 1000.
  * 'ಎರಡು ನೂರ ಐವತ್ತು' = 250, 'ಐದು ನೂರು' = 500, 'ಒಂದು ಸಾವಿರ' = 1000.

Return STRICT JSON matching this schema:
{
  "intent": "RECORD_CREDIT | RECORD_PAYMENT | RECORD_PROMISE | FULFILL_PROMISE | QUERY_BALANCE | QUERY_HISTORY | QUERY_REMINDERS | CONFIRM | CANCEL | CORRECT | UNKNOWN",
  "customer_name": "string or null",
  "amount": number_or_null,
  "transaction_type": "CREDIT | PAYMENT | PROMISE | FULFILL_PROMISE | null",
  "promised_date": "string or null",
  "language_detected": "kn | hi | en | mixed",
  "confidence": 0.95,
  "raw_utterance": "original text"
}
"""

STOPWORDS = {
    # English
    "i", "me", "my", "we", "our", "you", "he", "she", "it", "they", "this", "that",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "of", "from", "by", "about", "into", "through", "during", "before", "after",
    "is", "was", "are", "were", "be", "have", "has", "had", "do", "does", "did",
    "credit", "udhar", "payment", "paid", "rupees", "rs", "inr", "please", "record",
    "add", "give", "took", "take", "given", "received", "balance", "jama", "khathe",
    "khata", "yes", "no", "ok", "okay", "haan", "sari", "houdu",
    "needi", "kodi", "kottu", "le", "diya", "liya", "today", "yesterday", "due",
    "promise", "promised", "promising", "deposit", "will", "pay", "tomorrow", "remind",
    "reminder", "reminders", "date", "who", "has", "when",
    "fulfill", "fulfilled", "fulfilling", "complete", "completed", "pura", "poora", "chuka", "chukaya",
    "पूरा", "पक्का", "चुका",
    "ಪೂರ್ಣ", "ತೀರಿಸಿದರು", "ಮುಗಿದಿದೆ", "ಮುಗಿಯಿತು",
    # Hindi particles, verbs, and honorifics
    "को", "का", "के", "की", "से", "ने", "में", "पर", "रुपये", "रुपए", "रु", "उधार",
    "जमा", "दिया", "दिए", "लिया", "लिए", "चुकाए", "प्राप्त", "हुए", "खाता", "पे",
    "पेमेंट", "भैया", "जी", "बाबू", "अंकल", "सेठ", "सर", "है", "था", "थी", "थे", "हो",
    "करो", "कर", "दी", "गया", "गई", "गए", "वापस", "पैसे", "रोकड़", "रकम", "कल", "परसों",
    "वादा", "देगा", "देंगे", "देगी", "तारीख", "तारीख को", "आज", "किसका", "आना", "पूरा", "पूरे", "पूरी",
    # Common grocery words (to avoid taking items as customer names)
    "आटा", "चावल", "दाल", "तेल", "दूध", "शक्कर", "चीनी", "चाय", "साबुन", "बिस्कुट",
    # Kannada particles, verbs, and honorifics
    "ಗೆ", "ಇಂದ", "ನಲ್ಲಿ", "ರೂಪಾಯಿ", "ರೂ", "ಕ್ರೆಡಿಟ್", "ಉದ್ಧಾರ", "ಸಾಲ", "ಪಾವತಿ",
    "ಕೊಟ್ಟರು", "ನೀಡಿದರು", "ಖಾತೆ", "ಅಣ್ಣ", "ಅವರಿಗೆ", "ಅವ್ರಿಗೆ", "ಜಮಾ", "ಬಂತು",
    "ಆಗಿದೆ", "ಹಾಕಿ", "ಮಾಡಿ", "ದುಡ್ಡು", "ಅಕ್ಕಿ", "ಬೇಳೆ", "ಎಣ್ಣೆ", "ಹಾಲು", "ನಾಳೆ",
    "ಕೊಡುತ್ತಾರೆ", "ಕೊಡ್ತಾರೆ", "ಭರವಸೆ", "ಇಂದು"
}

NUMBER_WORDS = {
    "ondhu": 1, "ondu": 1, "ek": 1, "one": 1,
    "eradu": 2, "do": 2, "two": 2,
    "mooru": 3, "teen": 3, "three": 3,
    "naalku": 4, "chaar": 4, "four": 4,
    "aidu": 5, "paanch": 5, "panch": 5, "five": 5,
    "aaru": 6, "chhah": 6, "six": 6,
    "elu": 7, "saat": 7, "seven": 7,
    "entu": 8, "aath": 8, "eight": 8,
    "ombhatthu": 9, "nau": 9, "nine": 9,
    "hatthu": 10, "das": 10, "ten": 10,
    "nooru": 100, "sau": 100, "hundred": 100, "hundreds": 100,
    "saavira": 1000, "hajaar": 1000, "hazar": 1000, "thousand": 1000, "thousands": 1000, "thousandth": 1000,
}


from datetime import datetime, timedelta

def extract_promise_date(text: str) -> tuple[str, str]:
    lower = text.lower()
    now = datetime.now()

    # Today / aaj / ivatthu
    if any(w in lower for w in ["today", "aaj", "ivattu", "ivatthu", "आज"]):
        return now.strftime("%d %b %Y"), now.strftime("%Y-%m-%d")

    # Tomorrow / kal / nale
    if any(w in lower for w in ["tomorrow", "kal", "nale", "कल"]):
        due = now + timedelta(days=1)
        return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")

    # Day after tomorrow / parso
    if any(w in lower for w in ["day after tomorrow", "parso", "परसों"]):
        due = now + timedelta(days=2)
        return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")

    # Weekdays: monday, tuesday, etc.
    weekdays = {
        'monday': 0, 'somavara': 0, 'somwar': 0, 'सोमवार': 0,
        'tuesday': 1, 'mangalwar': 1, 'mangalavara': 1, 'मंगलवार': 1,
        'wednesday': 2, 'budhwar': 2, 'budhavara': 2, 'बुधवार': 2,
        'thursday': 3, 'guruwar': 3, 'guruvara': 3, 'गुरुवार': 3,
        'friday': 4, 'shukrawar': 4, 'shukravara': 4, 'शुक्रवार': 4,
        'saturday': 5, 'shaniwar': 5, 'shanivara': 5, 'शनिवार': 5,
        'sunday': 6, 'ravivar': 6, 'bhanuvara': 6, 'रविवार': 6,
    }
    for day_name, target_day in weekdays.items():
        if day_name in lower:
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            due = now + timedelta(days=days_ahead)
            return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")

    # Explicit date with month e.g. "25 nov", "25 november", "24 december"
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*', lower)
    if match:
        day = int(match.group(1))
        m_str = match.group(2)[:3]
        m = months.get(m_str, now.month)
        year = now.year if m >= now.month else now.year + 1
        try:
            due = datetime(year, m, day)
            return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")
        except:
            pass

    # Numeric day e.g. "25 ko", "26 tarikh", "26 तारीख"
    num_day_match = re.search(r'\b(\d{1,2})\s*(?:ko|tarikh|तारीख|th|st|nd|rd)\b', lower)
    if num_day_match:
        day = int(num_day_match.group(1))
        if 1 <= day <= 31:
            try:
                due = datetime(now.year, now.month, day)
                if due < now:
                    m = now.month + 1 if now.month < 12 else 1
                    y = now.year if now.month < 12 else now.year + 1
                    due = datetime(y, m, day)
                return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")
            except:
                pass

    # Default to tomorrow
    due = now + timedelta(days=1)
    return due.strftime("%d %b %Y"), due.strftime("%Y-%m-%d")


class LLMNLUService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.warning("Error re-configuring Gemini: %s", e)

    def _mock_extract(self, transcript: str, language: str = "kn") -> NLUResult:
        raw_text = transcript.strip()
        # Normalize comma-formatted numbers e.g. "15,000" or "1,50,000" -> "15000", "150000"
        clean_text = re.sub(r'(\d+),\s*(?=\d{3}(?:\D|$))', r'\1', raw_text)
        clean_text = re.sub(r'(?<=\d),(?=\d)', '', clean_text)
        text = clean_text
        lower = text.lower()

        # 1. Determine Intent
        intent = VoiceIntent.UNKNOWN
        tx_type = None
        promised_date = None

        confirm_words = [
            "yes", "haan", "sari", "houdu", "okay", "ok", "theek hai", "confirm", "done",
            "ha", "हाँ", "हा", "हاں", "सही", "सत्य", "श्योर", "ठीक", "ठीक है", "करो", "कर दो", "दर्ज करो",
            "ಹೌದು", "ಸರಿ", "ಖಚಿತ", "ಮಾಡಿ", "ದಾಖಲಿಸಿ", "yes confirm"
        ]
        cancel_words = [
            "no", "nahi", "beda", "cancel", "mat karo", "नहीं", "ना", "मत करो", "रद्द",
            "ಬೇಡ", "ಇಲ್ಲ", "ಕ್ಯಾನ್ಸಲ್", "na"
        ]
        reminder_words = [
            "remind", "reminder", "reminders", "who has to pay", "kis kis ka payment", "kiska payment",
            "aaj ka reminder", "today reminder", "due today", "aaj kiska", "aaj kisko", "yaaru kodbeku",
            "ಯಾರು ಕೊಡಬೇಕು", "ಇವತ್ತು ಯಾರು", "ರಿಮೈಂಡರ್", "रिमाइंडर", "किसका पैसा आना है", "आज किसका पेमेंट है",
            "किसने वादा किया था", "today promises", "promises today"
        ]
        fulfill_promise_words = [
            "fulfill promise", "fulfilled promise", "promise fulfilled", "promise complete", "promise completed",
            "promise paid", "paid his promise", "paid her promise", "paid promise", "mark promise as fulfilled",
            "fulfill the promise", "fulfill my promise", "promise done", "promise clear", "promise cleared",
            "vaada pura", "vada pura", "promise pura", "promise fulfill", "vaada poora", "promise poora",
            "vaada chuka", "vaada nipta", "vaada kar diya", "paise de diye", "promise chukaya", "promise chuka diya",
            "bhravase poorna", "bharavase poorna", "bharavase poornagolisi",
            "ಭರವಸೆ ಪೂರ್ಣ", "ಪ್ರಾಮಿಸ್ ಕಂಪ್ಲೀಟ್", "ಭರವಸೆ ಮುಗಿದಿದೆ", "ಭರವಸೆ ತೀರಿಸಿದ್ದಾರೆ", "ಪ್ರಾಮಿಸ್ ಫುಲ್ಫಿಲ್",
            "ಮಾತು ಉಳಿಸಿಕೊಂಡಿದ್ದಾರೆ", "ಭರವಸೆ ಪಾವತಿಸಲಾಗಿದೆ"
        ]
        promise_words = [
            "promise", "promised", "promising", "vaada", "vada", "dega", "denge", "degi",
            "will pay", "will deposit", "will give", "dene ka vaada", "dene bola", "dene boli",
            "kodthane", "kodthare", "kodtini", "ಕೊಡುತ್ತಾರೆ", "ಕೊಡ್ತೀನಿ", "ಕೊಡ್ತಾರೆ", "ಭರವಸೆ", "ವಚನ", "ತೀರಿಸುತ್ತೇನೆ",
            "वादा", "देगा", "देंगे", "देगी", "जमा करेगा", "जमा करेगी", "पेमेंट करेगा"
        ]
        payment_words = [
            "payment", "diye", "paid", "jama", "waapas", "received", "deposit", "settled",
            "जमा", "प्राप्त", "चुकाए", "भुगतान", "दिए", "वापस", "पैसे दिए", "पेमेंट",
            "ಪಾವತಿ", "ಜಮಾ", "ಕೊಟ್ಟರು", "ಬಂತು", "ಪಡೆದರು", "ಚುಕ್ತಾ"
        ]
        credit_words = [
            "udhar", "credit", "liya", "le gaya", "took", "due",
            "उधार", "उधार दिया", "बाकी", "लिखो", "खाते में",
            "ನೀಡಿ", "ಕ್ರೆಡಿಟ್", "ಸಾಲ", "ಉದ್ಧಾರ", "ತೆಗೆದುಕೊಂಡರು"
        ]

        tokens = set(lower.split())
        if any(w in tokens for w in ["yes", "haan", "sari", "houdu", "confirm", "done", "ha", "हाँ", "हा", "हೌದು", "ಸರಿ"]):
            intent = VoiceIntent.CONFIRM
        elif any(w in tokens for w in ["no", "nahi", "beda", "cancel", "नहीं", "ना", "ಬೇಡ"]):
            intent = VoiceIntent.CANCEL
        elif any(w in lower for w in reminder_words):
            intent = VoiceIntent.QUERY_REMINDERS
        elif any(w in lower for w in fulfill_promise_words) or (
            ("promise" in lower or "vaada" in lower or "vada" in lower or "bharavase" in lower or "वादा" in text or "प्रॉमिस" in text or "ಭರವಸೆ" in text or "ವಚನ" in text)
            and any(w in lower or w in text for w in ["fulfill", "fulfilled", "complete", "completed", "paid", "done", "cleared", "pura", "poora", "chuka", "पूरा", "पूरे", "पूरी", "चुका", "चुकता", "ನಿपटा", "ಪೂರ್ಣ", "ತೀರಿಸಿದೆ", "ತೀರಿಸಿದ್ದಾರೆ", "ಮುಗಿದಿದೆ", "ಕಂಪ್ಲೀಟ್", "ಪೂರ್ಣಗೊಂಡಿದೆ"])
        ):
            intent = VoiceIntent.FULFILL_PROMISE
            tx_type = "FULFILL_PROMISE"
        elif any(w in lower for w in promise_words) or ("will" in lower and any(p in lower for p in ["pay", "deposit", "give"])):
            intent = VoiceIntent.RECORD_PROMISE
            tx_type = "PROMISE"
            disp_date, _ = extract_promise_date(text)
            promised_date = disp_date
        elif any(w in lower for w in ["balance", "kitna baaki", "outstanding", "ಬಾಕಿ ಎಷ್ಟು", "how much balance", "कितना बाकी", "बैलेंस"]):
            intent = VoiceIntent.QUERY_BALANCE
        elif any(w in lower for w in ["history", "pichle", "transactions", "ವಹಿವಾಟು", "itahaas", "पिछला"]):
            intent = VoiceIntent.QUERY_HISTORY
        elif any(w in lower for w in payment_words) or ("from " in lower and "credit" not in lower):
            intent = VoiceIntent.RECORD_PAYMENT
            tx_type = "PAYMENT"
        elif any(w in lower for w in credit_words) or ("to " in lower and "payment" not in lower and "paid" not in lower):
            intent = VoiceIntent.RECORD_CREDIT
            tx_type = "CREDIT"
        else:
            digits = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", lower)
            if digits or any(w in lower for w in ("thousand", "thousands", "thousandth", "sau", "hazar", "hundred", "saavira")):
                intent = VoiceIntent.RECORD_CREDIT
                tx_type = "CREDIT"

        # 2. Extract Amount
        amount = None
        amt_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)', raw_text, re.IGNORECASE)
        if amt_match and amt_match.group(1):
            try:
                amount = float(amt_match.group(1).replace(',', '').strip())
            except ValueError:
                amount = None

        if amount is None:
            amt_match2 = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
            if amt_match2 and amt_match2.group(1):
                try:
                    amount = float(amt_match2.group(1))
                except ValueError:
                    amount = None

        if amount is None:
            clean_tokens = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in lower.split()]
            for i in range(len(clean_tokens) - 1):
                w1, w2 = clean_tokens[i], clean_tokens[i + 1]
                if w1 in NUMBER_WORDS and w2 in ("nooru", "sau", "hundred", "hundreds"):
                    amount = float(NUMBER_WORDS[w1] * 100)
                    break
                elif w1 in NUMBER_WORDS and w2 in ("saavira", "hajaar", "hazar", "thousand", "thousands", "thousandth"):
                    amount = float(NUMBER_WORDS[w1] * 1000)
                    break

            if amount is None:
                for w in clean_tokens:
                    if w in ("saavira", "hajaar", "hazar", "thousand", "thousands", "thousandth"):
                        amount = 1000.0
                        break
                    elif w in ("nooru", "sau", "hundred", "hundreds"):
                        amount = 100.0
                        break

        # 3. Extract Customer Name with smart Indic & English pattern matching
        customer_name = None
        lower_clean = re.sub(r'[₹।\.,!?\'\":;\(\)\[\]/\\]', ' ', text)

        # Pattern -1: Fulfill Promise: "fulfill promise of/for <name>", "<name> promise fulfilled", "<name> ka vaada pura"
        if intent == VoiceIntent.FULFILL_PROMISE:
            f_match1 = re.search(
                r'(?:fulfill|complete|clear|received)\s+(?:the\s+)?(?:promise|vaada|vada|bharavase)\s+(?:of|for|from)?\s+([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)',
                lower_clean,
                re.IGNORECASE
            )
            if f_match1:
                cand = f_match1.group(1).strip()
                cand_words = [w for w in cand.split() if w.lower() not in STOPWORDS]
                if cand_words:
                    customer_name = " ".join(cand_words[:2])
            if not customer_name:
                f_match2 = re.search(
                    r'([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:ka|ki|ke|avara|avarige|ne|का|के|की|ने|ಅವರ|ಅವರಿಗೆ)?\s*(?:promise|vaada|vada|bharavase|वादा|प्रॉमिस|ಭರವಸೆ|ವಚನ)\s+(?:fulfilled|complete|completed|pura|poora|chuka|done|cleared|पूरा|पूरे|पूरी|चुका|ಪೂರ್ಣ|ಮುಗಿದಿದೆ|ತೀರಿಸಿದ್ದಾರೆ|ಪೂರ್ಣಗೊಂಡಿದೆ)',
                    lower_clean,
                    re.IGNORECASE
                )
                if f_match2:
                    cand = f_match2.group(1).strip()
                    cand = re.sub(r'\s+(?:ka|ki|ke|avara|avarige|ne|का|के|की|ने|ಅವರ|ಅವರಿಗೆ)$', '', cand).strip()
                    cand_words = [w for w in cand.split() if w.lower() not in STOPWORDS]
                    if cand_words:
                        customer_name = " ".join(cand_words[:2])

        # Pattern 0: Promise pattern: "<name> promised to...", "<name> will pay...", "<name> kal ... dega"
        prom_match = re.search(
            r'^\s*([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:promised|promise|will|ne|kal|parso|nale)\b',
            lower_clean,
            re.IGNORECASE
        )
        if prom_match:
            cand = prom_match.group(1).strip()
            cand_words = [w for w in cand.split() if w.lower() not in STOPWORDS]
            if cand_words:
                customer_name = " ".join(cand_words[:2])

        # Pattern A: "payment/credit from <name>", "to <name>", "for <name>", "of <name>"
        # e.g. "payment of 800 from ravi" -> "ravi"
        if not customer_name:
            from_to_match = re.search(
                r'\b(?:from|to|for|se|ko|from\s+the)\s+([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)',
                lower_clean,
                re.IGNORECASE
            )
            if from_to_match:
                candidate = from_to_match.group(1).strip()
                cand_words = [w for w in candidate.split() if w.lower() not in STOPWORDS]
                if cand_words:
                    customer_name = " ".join(cand_words[:2])

        # Pattern B: Indic postposition pattern: "<name> ko", "<name> se", "<name> ke", "<name> avarige"
        if not customer_name:
            indic_match = re.search(
                r'([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:ko|se|ka|ke|ki|ne|avara|avarige|avru)\b',
                lower_clean,
                re.IGNORECASE
            )
            if indic_match:
                candidate = indic_match.group(1).strip()
                cand_words = [w for w in candidate.split() if w.lower() not in STOPWORDS]
                if cand_words:
                    customer_name = " ".join(cand_words[:2])

        # Pattern C: Fallback token filter
        if not customer_name:
            words = lower_clean.split()
            candidates = []
            for word in words:
                w_lower = word.lower()
                if w_lower in STOPWORDS or re.match(r'^\d+(\.\d+)?$', word) or w_lower in NUMBER_WORDS:
                    continue
                candidates.append(word)
            if candidates:
                customer_name = " ".join(candidates[:2])

        # Clean any stray honorifics or leading prepositions
        if customer_name:
            customer_name = re.sub(r'^(?:of|from|to|for|the|a)\s+', '', customer_name, flags=re.IGNORECASE).strip()

        if intent == VoiceIntent.QUERY_REMINDERS:
            customer_name = None

        detected_lang = language
        if any('\u0c80' <= char <= '\u0cff' for char in text):
            detected_lang = "kn"
        elif any('\u0900' <= char <= '\u097f' for char in text):
            detected_lang = "hi"

        return NLUResult(
            intent=intent,
            customer_name=customer_name,
            amount=amount,
            transaction_type=tx_type,
            promised_date=promised_date,
            language_detected=detected_lang,
            confidence=0.92,
            raw_utterance=transcript,
        )

    async def extract(
        self,
        transcript: str,
        language: str = "kn",
        history: Optional[List[Dict[str, Any]]] = None
    ) -> NLUResult:
        # Pre-clean comma numbers e.g. "15,000" -> "15000"
        clean_transcript = re.sub(r'(\d+),\s*(?=\d{3}(?:\D|$))', r'\1', transcript.strip())
        clean_transcript = re.sub(r'(?<=\d),(?=\d)', '', clean_transcript)

        # If API key is available, use Google Gemini (gemini-2.5-flash)
        if self.api_key:
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
                )

                prompt = f"""Conversation history: {json.dumps(history or [])}
Spoken text: "{clean_transcript}"
Detected audio language hint: "{language}"
"""
                response = await asyncio.wait_for(
                    model.generate_content_async(
                        contents=[
                            {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + prompt]}
                        ]
                    ),
                    timeout=3.5
                )

                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                data = json.loads(response_text.strip())

                intent_str = data.get("intent", "UNKNOWN")
                try:
                    intent_enum = VoiceIntent(intent_str)
                except ValueError:
                    intent_enum = VoiceIntent.UNKNOWN

                amount = data.get("amount")
                if amount is not None:
                    try:
                        if isinstance(amount, str):
                            amount = float(amount.replace(',', '').strip())
                        else:
                            amount = float(amount)
                    except (ValueError, TypeError):
                        amount = None

                # Safety guard for comma numbers: if spoken text has e.g. 15,000 or 15000 and amount was parsed as 15
                thousand_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})+|\d{4,})', transcript, re.IGNORECASE)
                if thousand_match:
                    full_num = float(thousand_match.group(1).replace(',', ''))
                    if amount is not None and amount < 100 and full_num >= 1000:
                        logger.info("Correcting truncated amount %s to %s from transcript", amount, full_num)
                        amount = full_num

                # Safety guard for FULFILL_PROMISE: if transcript mentions fulfillment and promise
                fulfill_markers = ["पूरा", "pura", "poora", "fulfilled", "fulfill", "complete", "completed", "done", "chuka", "चुकता", "पೂರ್ಣ", "ತೀರಿಸಿದ್ದಾರೆ", "ಮುಗಿದಿದೆ"]
                promise_markers = ["वादा", "vaada", "vada", "promise", "ಭರವಸೆ", "ವಚನ"]
                lower_trans = clean_transcript.lower()
                if any(fm in lower_trans or fm in clean_transcript for fm in fulfill_markers) and any(pm in lower_trans or pm in clean_transcript for pm in promise_markers):
                    intent_enum = VoiceIntent.FULFILL_PROMISE

                cust_name = data.get("customer_name")
                if cust_name:
                    cust_name = str(cust_name).strip()
                    if cust_name.lower() in ("null", "none", ""):
                        cust_name = None
                    else:
                        # Strip common verbal trailing particles like "हो", "गया", "कर", "दिया", "ने", "का", "की", "के"
                        cust_name = re.sub(r'\s+(?:हो|गया|गई|कर|दिया|दिए|ने|का|की|के|ಇಂದ|ಅವರ|ಅವರಿಗೆ|avara|avarige)$', '', cust_name).strip()

                promised_date = data.get("promised_date")
                if intent_enum == VoiceIntent.RECORD_PROMISE and not promised_date:
                    disp_d, _ = extract_promise_date(transcript)
                    promised_date = disp_d

                logger.info(
                    "Gemini 2.5 NLU parsed: intent=%s, type=%s, customer=%s, amount=%s, promise_date=%s",
                    intent_enum,
                    data.get("transaction_type"),
                    cust_name,
                    amount,
                    promised_date,
                )

                return NLUResult(
                    intent=intent_enum,
                    customer_name=cust_name,
                    amount=amount,
                    transaction_type=data.get("transaction_type"),
                    promised_date=promised_date,
                    language_detected=data.get("language_detected", language),
                    confidence=float(data.get("confidence", 0.95)),
                    raw_utterance=transcript,
                )

            except Exception as e:
                logger.warning("Gemini 2.5 NLU call failed (%s). Using fallback extractor.", e)

        # Fallback to local heuristic extractor
        return self._mock_extract(transcript, language)

    async def generate_response(self, intent: str, context: dict) -> str:
        lang = context.get("language", "kn")
        cust = context.get("customer_name", "Customer")
        amt = context.get("amount", 0)
        bal = context.get("new_balance", 0)

        if intent == "RECORD_CREDIT":
            if lang == "kn":
                return f"{cust} ಅವರಿಗೆ ₹{amt:,.0f} ಸಾಲ ದಾಖಲಿಸಬೇಕೇ? ದೃಢೀಕರಿಸಿ."
            elif lang == "hi":
                return f"{cust} के लिए ₹{amt:,.0f} उधार दर्ज करें? कृपया पुष्टि करें।"
            return f"Record ₹{amt:,.0f} credit for {cust}?"

        elif intent == "RECORD_PAYMENT":
            if lang == "kn":
                return f"{cust} ಅವರಿಂದ ₹{amt:,.0f} ಜಮಾ (ಪಾವತಿ) ದಾಖಲಿಸಬೇಕೇ? ದೃಢೀಕರಿಸಿ."
            elif lang == "hi":
                return f"{cust} से ₹{amt:,.0f} जमा (भुगतान) प्राप्त हुआ? कृपया पुष्टि करें।"
            return f"Record ₹{amt:,.0f} payment received from {cust}?"

        elif intent == "RECORD_PROMISE":
            p_date = context.get("promised_date", "scheduled date")
            if lang == "kn":
                return f"ಗುರುತು ಮಾಡಲಾಗಿದೆ! {cust} ಅವರು {p_date} ರಂದು ₹{amt:,.0f} ಕೊಡುವುದಾಗಿ ಭರವಸೆ ನೀಡಿದ್ದಾರೆ."
            elif lang == "hi":
                return f"नोट कर लिया गया! {cust} ने {p_date} को ₹{amt:,.0f} देने का वादा किया है।"
            return f"Noted! {cust} has promised to deposit ₹{amt:,.0f} on {p_date}."

        elif intent == "FULFILL_PROMISE":
            if lang == "kn":
                return f"{cust} ಅವರ ಪಾವತಿ ಭರವಸೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಾಗಿದೆ (Fulfilled)!"
            elif lang == "hi":
                return f"{cust} का वादा सफलतापूर्वक पूरा (Fulfilled) दर्ज कर लिया गया है!"
            return f"Payment promise for {cust} has been marked as fulfilled!"

        elif intent == "QUERY_REMINDERS":
            if lang == "kn":
                return "ಇಂದಿನ ಪಾವತಿ ಜ್ಞಾಪನೆಗಳು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ."
            elif lang == "hi":
                return "आज के पेमेंट रिमाइंडर्स की जाँच की जा रही है।"
            return "Checking today's payment reminders."

        elif intent == "CONFIRM":
            if lang == "kn":
                return f"ಖಾತೆ ನವೀಕರಿಸಲಾಗಿದೆ. {cust} ಅವರ ಹೊಸ ಬಾಕಿ ₹{bal:,.0f}."
            elif lang == "hi":
                return f"खाता अपडेट हो गया है। {cust} का नया बकाया ₹{bal:,.0f} है।"
            return f"Transaction confirmed! New balance for {cust} is ₹{bal:,.0f}."

        return "How can I help with your khata today?"


class LLMNLUProcessor(PipelineProcessor):
    def __init__(self):
        self.service = LLMNLUService()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.skip_to_tts or ctx.error:
            return ctx

        if not ctx.transcript:
            ctx.error = "No transcript available for reasoning"
            return ctx

        result = await self.service.extract(
            transcript=ctx.transcript,
            language=ctx.language,
            history=ctx.conversation_history
        )

        ctx.nlu_result = result
        return ctx
