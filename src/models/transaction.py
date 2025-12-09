from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Integer, nullable=False)
    operation_type = Column(String(30), nullable=False)  # add / subtract
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # 🔥 ОБЯЗАТЕЛЬНО — чтобы User.transactions заработал
    user = relationship(
        "User",
        back_populates="transactions"
    )
