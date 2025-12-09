# src/repositories/transaction_repository.py

from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ----------------------------------------
    #               CREATE
    # ----------------------------------------
    async def create(
        self,
        user_id: int,
        amount: int,
        operation_type: str,
        description: str = "",
        category: str = "bonus",
        admin_id: int = None
    ) -> dict:

        tx = Transaction(
            user_id=user_id,
            amount=amount,
            operation_type=operation_type,
            description=description,
            category=category
        )

        self.session.add(tx)
        await self.session.flush()  # чтобы tx.id стал доступен

        return {
            "id": tx.id,
            "user_id": tx.user_id,
            "amount": tx.amount,
            "operation_type": tx.operation_type,
            "description": tx.description,
            "category": tx.category,
            "created_at": tx.created_at
        }

    # ----------------------------------------
    #     USER TRANSACTIONS
    # ----------------------------------------
    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Transaction]:

        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.id))
            .limit(limit)
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()

    # ----------------------------------------
    #        ALL TRANSACTIONS
    # ----------------------------------------
    async def get_all_transactions(self, limit: int = 50) -> List[Transaction]:

        stmt = (
            select(Transaction)
            .order_by(desc(Transaction.id))
            .limit(limit)
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()

    # ----------------------------------------
    #     RECENT TRANSACTIONS (N DAYS)
    # ----------------------------------------
    async def get_recent_transactions(self, days: int = 7) -> List[Transaction]:

        cutoff = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(Transaction)
            .where(Transaction.created_at >= cutoff)
            .order_by(desc(Transaction.id))
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()

    # ----------------------------------------
    #     BALANCE CHANGE FOR PERIOD
    # ----------------------------------------
    async def get_user_balance_change(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> int:

        stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date
            )
        )

        res = await self.session.execute(stmt)
        txs = res.scalars().all()

        balance_change = 0

        for t in txs:
            if t.operation_type == "add":
                balance_change += t.amount
            else:
                balance_change -= t.amount

        return balance_change
