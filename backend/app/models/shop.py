from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    language_preference = Column(String(10), default="kn", nullable=False)
    demo_mode = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    customers = relationship("Customer", back_populates="shop", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="shop", cascade="all, delete-orphan")
    transaction_drafts = relationship("TransactionDraft", back_populates="shop", cascade="all, delete-orphan")
