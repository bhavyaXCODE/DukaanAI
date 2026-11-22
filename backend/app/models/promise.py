from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PaymentPromise(Base):
    __tablename__ = "payment_promises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    promise_date = Column(String(100), nullable=False)  # Display string e.g. "25 Nov 2026" or "Tomorrow"
    due_date = Column(String(50), nullable=True)        # Format YYYY-MM-DD for date comparison
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING | FULFILLED | DISMISSED
    voice_transcript = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer")
