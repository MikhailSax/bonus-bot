import sqlite3
import sys
import types


if "aiosqlite" not in sys.modules:
    fake = types.ModuleType("aiosqlite")

    class _FakeConnection:
        daemon = True

        def __await__(self):
            async def _dummy():
                return self
            return _dummy().__await__()

    def _connect(*args, **kwargs):
        return _FakeConnection()

    fake.connect = _connect
    for name in (
        "DatabaseError",
        "Error",
        "IntegrityError",
        "NotSupportedError",
        "OperationalError",
        "ProgrammingError",
        "sqlite_version",
        "sqlite_version_info",
    ):
        setattr(fake, name, getattr(sqlite3, name))

    sys.modules["aiosqlite"] = fake
