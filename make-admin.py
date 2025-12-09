import asyncio
from sqlalchemy import text
from src.database import engine

TG_ID = 303315496  # ← поставь свой Telegram ID


async def make_admin():
    sql = text("""
        UPDATE users
        SET role = 'admin'
        WHERE telegram_id = :tg_id
    """)

    async with engine.begin() as conn:
        await conn.execute(sql, {"tg_id": TG_ID})

    print(f"✅ Пользователь {TG_ID} назначен администратором!")


if __name__ == "__main__":
    asyncio.run(make_admin())
