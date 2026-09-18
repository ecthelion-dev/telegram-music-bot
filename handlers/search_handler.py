import os
import logging
from aiogram import Router, types, F, Bot
from aiogram.types import FSInputFile
from aiogram.enums import ChatAction
from services.download_service import download_track_by_query
from handlers.feedback import format_error
from database import get_cached_track, save_track

logger = logging.getLogger(__name__)
router = Router(name="search_router")

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_search(message: types.Message, bot: Bot):
    query = message.text.strip()
    if len(query) < 2:
        await message.reply("Iltimos, qo‘shiq nomini to‘liqroq yozing.")
        return

    # Check database cache first
    cached = await get_cached_track(query)
    if cached and cached.get("telegram_file_id"):
        await message.reply_audio(
            audio=cached["telegram_file_id"],
            caption=f"🎧 <b>{cached.get('artist', '')} - {cached.get('title', '')}</b>\n<i>(Tezkor keshdan yuborildi)</i>",
            parse_mode="HTML"
        )
        return

    status_msg = await message.reply(f"🔎 <b>'{query}'</b> qidirilmoqda...", parse_mode="HTML")
    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)

    try:
        download_result = await download_track_by_query(query)

        if download_result.get("error"):
            await status_msg.edit_text(format_error(download_result, message.from_user.id))
            return

        mp3_path = download_result.get("file_path")
        if not mp3_path or not os.path.exists(mp3_path):
            await status_msg.edit_text("❌ Audio faylni yuklab olishda xatolik yuz berdi.")
            return

        title = download_result.get("title", query)
        artist = download_result.get("artist", "")
        duration = download_result.get("duration", 0)

        audio_file = FSInputFile(mp3_path, filename=f"{artist} - {title}.mp3" if artist else f"{title}.mp3")
        sent_audio = await message.reply_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=duration,
            caption=f"🎵 <b>{artist} - {title}</b>" if artist else f"🎵 <b>{title}</b>",
            parse_mode="HTML"
        )

        # Save to database cache
        if sent_audio.audio:
            await save_track(
                query_key=query,
                title=title,
                artist=artist,
                telegram_file_id=sent_audio.audio.file_id,
                duration=sent_audio.audio.duration or duration
            )

        # Clean up local mp3
        try:
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
        except Exception as e:
            logger.warning("Could not delete local mp3: %s", e)

        await status_msg.delete()

    except Exception as e:
        logger.error("Error in text search handler: %s", e, exc_info=True)
        await status_msg.edit_text("⚠️ Qidiruv jarayonida xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.")
