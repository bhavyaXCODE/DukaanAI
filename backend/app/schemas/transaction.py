from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TransactionBase(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    type: str  # CREDIT / PAYMENT
    amount: float
    description: Optional[str] = None
    voice_transcript: Optional[str] = None


class TransactionCreate(TransactionBase):
    shop_id: Optional[int] = 1


class TransactionResponse(TransactionBase):
    id: int
    shop_id: int
    customer_name: Optional[str] = None
    status: str
    session_id: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    size: int


class DashboardStats(BaseModel):
    total_outstanding: float
    credit_today: float
    credit_today_pct_change: float
    payments_today: float
    payments_today_pct_change: float
    active_customers: int
    transactions_today: int


class DailyChartPoint(BaseModel):
    date: str
    credit: float
    payment: float
    day: Optional[str] = None
