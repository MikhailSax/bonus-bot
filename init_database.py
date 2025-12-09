# init_db.py
import asyncio
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.dirname(__file__))


async def init_database():
    print("🔧 Инициализация базы данных...")

    try:
        # Импортируем из вашего database.py
        from src.database import engine, Base, create_tables

        # Проверяем подключение
        from src.database import check_connection
        if await check_connection():
            print("✅ Подключение успешно!")

        # Импортируем модели (чтобы они зарегистрировались в Base)
        try:
            from src.models.user import User
            print("✅ Модель User импортирована")
        except ImportError as e:
            print(f"❌ Ошибка импорта User: {e}")
            print("Создайте файл src/models/user.py")
            return

        try:
            from src.models.transaction import Transaction
            print("✅ Модель Transaction импортирована")
        except ImportError as e:
            print(f"⚠️  Transaction не найден: {e}")

        try:
            from src.models.admin_action import AdminAction
            print("✅ Модель AdminAction импортирована")
        except ImportError as e:
            print(f"⚠️  AdminAction не найден: {e}")

        # Создаем таблицы
        await create_tables()

        print("\n🎉 База данных успешно инициализирована!")
        print("📁 Файл базы: bonus_bot.db")

    except Exception as e:
        print(f"❌ Ошибка при инициализации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(init_database())