from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel


class VoiceIntent(str, Enum):
    RECORD_CREDIT = "RECORD_CREDIT"
    RECORD_PAYMENT = "RECORD_PAYMENT"
    RECORD_PROMISE = "RECORD_PROMISE"
    FULFILL_PROMISE = "FULFILL_PROMISE"
    QUERY_BALANCE = "QUERY_BALANCE"
    QUERY_HISTORY = "QUERY_HISTORY"
    QUERY_REMINDERS = "QUERY_REMINDERS"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    CORRECT = "CORRECT"
    UNKNOWN = "UNKNOWN"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    INVALID = "INVALID"


class NLUResult(BaseModel):
    intent: VoiceIntent
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None  # CREDIT | PAYMENT | PROMISE | None
    promised_date: Optional[str] = None
    language_detected: str = "kn"
    confidence: float = 1.0
    raw_utterance: str


class PipelineResponse(BaseModel):
    state: str  # PROCESSING | CONFIRMING | SAVING | DONE | ERROR
    message: Optional[str] = None
    transaction_id: Optional[int] = None
    new_balance: Optional[float] = None
    has_audio: bool = False
    disambiguation_options: Optional[List[dict]] = None
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None
    promised_date: Optional[str] = None
    promised_amount: Optional[float] = None
