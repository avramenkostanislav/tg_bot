import aiosqlite
import config

async def _insert_user(telegram_user_id: int) -> None:
    async with aiosqlite.connect(config.SQLITE_DB_FILE) as db:
        await db.execute("insert or ignore into bot_user(telegram_id) values(:telegram_id)",
                         {"telegram_id": telegram_user_id})
        await db.commit()