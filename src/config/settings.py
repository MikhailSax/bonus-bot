from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str  # Оставляем как строку
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_ids_list(self) -> List[int]:
        """Преобразуем строку ADMIN_IDS в список int"""
        if not self.ADMIN_IDS:
            return []

        ids = []
        for part in self.ADMIN_IDS.split(","):
            part = part.strip()
            if part:
                try:
                    ids.append(int(part))
                except ValueError:
                    continue
        return ids


settings = Settings()