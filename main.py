import asyncio
import logging
import traceback

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, BOT_NAME
import database.db as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set!")

    logger.info("Initialising database...")
    await db.get_db()
    logger.info("Database ready.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    from commands import router as main_router
    dp.include_router(main_router)

    @dp.error()
    async def error_handler(update: object, exception: Exception):
        logger.error(f"Handler error: {exception}", exc_info=True)

    logger.info(f"Starting {BOT_NAME} bot...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await db.close()
        await bot.session.close()

async def main():
    retries = 0
    while True:
        try:
            retries = 0
            await run_bot()
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            retries += 1
            logger.error(f"Bot crashed (attempt {retries}): {e}")
            if retries >= 10:
                break
            await asyncio.sleep(min(5 * retries, 60))

if __name__ == "__main__":
    asyncio.run(main())
