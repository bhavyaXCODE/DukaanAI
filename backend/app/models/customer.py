from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    alias = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    landmark = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    outstanding_balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    promised_amount = Column(Numeric(12, 2), default=0.00, nullable=True)
    promised_date = Column(String(100), nullable=True)
    promise_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    shop = relationship("Shop", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    transaction_drafts = relationship("TransactionDraft", back_populates="resolved_customer")
