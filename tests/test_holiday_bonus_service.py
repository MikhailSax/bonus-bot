from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from src.models.user import User
from src.services.holiday_bonus_service import HolidayBonusService


class TestHolidayBonusService(IsolatedAsyncioTestCase):
    async def test_skip_holiday_award_on_registration_day(self):
        session = AsyncMock()
        user = User(telegram_id=1, birth_date=datetime.now().date(), created_at=datetime.now())
        user.id = 10
        session.get.return_value = user

        service = HolidayBonusService(session)
        service._expire_old_bonuses = AsyncMock()
        service._check_birthday_bonus = AsyncMock()
        service._check_calendar_holidays = AsyncMock()

        result = await service.check_and_award_user_bonuses(user.id)

        self.assertEqual(result, [])
        service._expire_old_bonuses.assert_awaited_once()
        service._check_birthday_bonus.assert_not_awaited()
        service._check_calendar_holidays.assert_not_awaited()
        session.commit.assert_awaited_once()

    async def test_award_checks_run_after_registration_day(self):
        session = AsyncMock()
        user = User(
            telegram_id=2,
            birth_date=datetime.now().date(),
            created_at=datetime.now() - timedelta(days=1),
        )
        user.id = 11
        session.get.return_value = user

        service = HolidayBonusService(session)
        service._expire_old_bonuses = AsyncMock()
        service._check_birthday_bonus = AsyncMock()
        service._check_calendar_holidays = AsyncMock()

        execute_result = Mock()
        execute_result.scalars.return_value.all.return_value = []
        session.execute.return_value = execute_result

        await service.check_and_award_user_bonuses(user.id)

        service._expire_old_bonuses.assert_awaited_once()
        service._check_birthday_bonus.assert_awaited_once()
        service._check_calendar_holidays.assert_awaited_once()
        session.commit.assert_awaited_once()
