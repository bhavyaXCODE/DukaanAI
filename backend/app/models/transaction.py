from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # CREDIT / PAYMENT
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    voice_transcript = Column(Text, nullable=True)
    status = Column(String(20), default="DRAFT", nullable=False)  # DRAFT / CONFIRMED / CANCELLED
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    shop = relationship("Shop", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")


class TransactionDraft(Base):
    __tablename__ = "transaction_drafts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_transcript = Column(Text, nullable=True)
    extracted_customer_name = Column(String(255), nullable=True)
    resolved_customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    extracted_amount = Column(Numeric(12, 2), nullable=True)
    extracted_type = Column(String(20), nullable=True)  # CREDIT / PAYMENT
    ambiguity_flag = Column(Boolean, default=False, nullable=False)
    ambiguity_reason = Column(Text, nullable=True)
    conversation_history = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    shop = relationship("Shop", back_populates="transaction_drafts")
    resolved_customer = relationship("Customer", back_populates="transaction_drafts")
