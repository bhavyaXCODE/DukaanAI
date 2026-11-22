from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class CustomerBase(BaseModel):
    name: str
    alias: Optional[str] = None
    phone: Optional[str] = None
    landmark: Optional[str] = None
    notes: Optional[str] = None
    promised_amount: Optional[float] = 0.0
    promised_date: Optional[str] = None
    promise_notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    shop_id: Optional[int] = 1
    outstanding_balance: Optional[float] = 0.0


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[str] = None
    phone: Optional[str] = None
    landmark: Optional[str] = None
    notes: Optional[str] = None
    outstanding_balance: Optional[float] = None
    promised_amount: Optional[float] = None
    promised_date: Optional[str] = None
    promise_notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    shop_id: int
    outstanding_balance: float
    total_credit: Optional[float] = 0.0
    total_payments: Optional[float] = 0.0
    promised_amount: Optional[float] = 0.0
    promised_date: Optional[str] = None
    promise_notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
