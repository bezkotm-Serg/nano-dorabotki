import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers.admin import router as admin_router
from handlers.common import router as common_router
from handlers.photos import router as photos_router
from storage.credits import init_db
from utils.config import cfg

# ── Логи
Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("logs/app.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("bot")


def _load_env() -> None:
    # why: централизуем загрузку .env из корня
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


async def main() -> None:
    _load_env()
    cfg.reload()  # прочитать ENV после load_dotenv
    if not cfg.bot_token:
        raise RuntimeError("В .env не указан BOT_TOKEN")

    init_db()

    bot = Bot(token=cfg.bot_token)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(photos_router)

    log.info("Бот запущен. MODE=%s FEATURE=%s", cfg.mode, cfg.feature)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logging.getLogger("fatal").exception("Фатальная ошибка: %s", e)
        sys.exit(1)
