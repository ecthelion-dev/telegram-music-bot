import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers.admin_handler import router as admin_router
from handlers.common import router as common_router
from handlers.social_handler import router as social_router
from handlers.voice_handler import router as voice_router
from handlers.search_handler import router as search_router
from handlers.inline_handler import router as inline_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

import os
from aiohttp import web

async def handle_health_check(request):
    return web.Response(text="Bot is running! 🎵", content_type="text/plain")

async def start_health_server():
    """Starts a minimal web server so platforms like Render/Koyeb don't terminate the app."""
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Healthcheck web server {port}-portda ishga tushdi.")
    except Exception as e:
        logger.warning(f"Healthcheck web server {port}-portda ishga tushmadi ({e}). Bot polling rejimida davom etmoqda.")


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("DIQQAT: .env faylida BOT_TOKEN ko'rsatilmagan!")
        print("\n" + "="*60)
        print("XATOLIK: BOT_TOKEN topilmadi!")
        print("Iltimos, .env faylini ochib, @BotFather bergan tokenni kiriting:")
        print("BOT_TOKEN=123456789:ABCDefghijk...")
        print("="*60 + "\n")
        sys.exit(1)

    # Initialize Database
    logger.info("Initializing database...")
    await init_db()

    # Start healthcheck web server (for Render/Koyeb)
    await start_health_server()

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register routers (order matters: admin and specialized handlers first)
    dp.include_router(admin_router)
    dp.include_router(common_router)
    dp.include_router(social_router)
    dp.include_router(voice_router)
    dp.include_router(search_router)
    dp.include_router(inline_router)

    logger.info("Bot ishga tushmoqda...")
    try:
        # Delete webhook if set and drop pending updates
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot o'chirildi.")
