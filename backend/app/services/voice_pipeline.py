from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class PipelineContext:
    session_id: str
    shop_id: int
    # Input
    audio_bytes: Optional[bytes] = None
    transcript: Optional[str] = None  # Set directly in mock mode
    language: str = "kn"
    confidence: float = 1.0
    # NLU
    nlu_result: Optional[Any] = None
    # Customer resolution
    confirmed_customer_id: Optional[int] = None
    confirmed_customer_name: Optional[str] = None
    disambiguation_options: Optional[List[dict]] = None
    # Pipeline flow
    pipeline_state: str = "PROCESSING"  # PROCESSING | CONFIRMING | SAVING | DONE | ERROR
    response_text: Optional[str] = None
    # Output
    tts_audio: Optional[bytes] = None
    has_audio: bool = False
    transaction_id: Optional[int] = None
    new_balance: Optional[float] = None
    # Draft
    draft_id: Optional[int] = None
    # Conversation
    conversation_history: List[dict] = field(default_factory=list)
    # Error
    error: Optional[str] = None
    skip_to_tts: bool = False  # Set True when only TTS response needed

    def to_response_dict(self) -> dict:
        return {
            "type": "STATE",
            "state": self.pipeline_state,
            "message": self.response_text,
            "transaction_id": self.transaction_id,
            "new_balance": self.new_balance,
            "has_audio": self.has_audio,
            "disambiguation_options": self.disambiguation_options,
            "customer_name": self.confirmed_customer_name or (self.nlu_result.customer_name if self.nlu_result else None),
            "amount": self.nlu_result.amount if self.nlu_result else None,
            "transaction_type": self.nlu_result.transaction_type if self.nlu_result else None,
            "promised_date": getattr(self.nlu_result, "promised_date", None) if self.nlu_result else None,
            "promised_amount": getattr(self, "promised_amount", None) or (self.nlu_result.amount if (self.nlu_result and getattr(self.nlu_result, "intent", None) == "RECORD_PROMISE") else None),
            "error": self.error,
        }


class PipelineProcessor(ABC):
    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        pass


class VoicePipeline:
    def __init__(self, processors: List[PipelineProcessor]):
        self.processors = processors

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        for processor in self.processors:
            if ctx.error:
                break
            ctx = await processor.process(ctx)
        return ctx
