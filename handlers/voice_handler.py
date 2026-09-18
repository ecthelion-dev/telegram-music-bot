import os
import uuid
import logging
from pathlib import Path
from aiogram import Router, types, F, Bot
from aiogram.types import FSInputFile
from aiogram.enums import ChatAction
from config import TEMP_DIR
from services.download_service import download_track_by_query
from handlers.feedback import format_error
from database import get_cached_track, save_track

logger = logging.getLogger(__name__)
router = Router(name="voice_router")

@router.message(F.voice | F.audio | F.video_note)
async def handle_audio_recognition(message: types.Message, bot: Bot):
    # 1. Identify file object
    telegram_file = message.voice or message.audio or message.video_note
    if not telegram_file:
        return

    status_msg = await message.reply("Eshitilmoqda va tahlil qilinmoqda... 🔍")
    await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)

    unique_id = uuid.uuid4().hex
    temp_file_path = TEMP_DIR / f"rec_{unique_id}.ogg"

    try:
        # 2. Download file to temp
        await bot.download(telegram_file, destination=temp_file_path)

        # Imported here, not at module scope: shazamio pulls in numpy, which costs
        # ~18 MB that a bot serving only text searches would never use.
        from services.shazam_service import recognize_audio_file

        track_info = await recognize_audio_file(str(temp_file_path))

        if not track_info:
            await status_msg.edit_text(
                "😔 Kechirasiz, musiqani aniqlab bo‘lmadi.\n\n"
                "Iltimos, musiqani balandroq va shovqinsizroq qilib, kamida 7-10 soniya yozib qayta yuboring."
            )
            return

        artist = track_info.get("artist") or "Noma'lum ijrochi"
        title = track_info.get("title") or "Noma'lum qo'shiq"
        query = track_info.get("query") or f"{artist} - {title}"

        await status_msg.edit_text(
            f"🎉 <b>Topildi:</b>\n"
            f"👤 <b>Ijrochi:</b> {artist}\n"
            f"🎵 <b>Qo‘shiq:</b> {title}\n\n"
            f"Audio yuklanmoqda... ⏳",
            parse_mode="HTML"
        )
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)

        # 4. Check cache in database
        cached = await get_cached_track(query)
        if cached and cached.get("telegram_file_id"):
            await message.reply_audio(
                audio=cached["telegram_file_id"],
                caption=f"🎧 <b>{artist} - {title}</b>\n<i>(Tezkor keshdan yuborildi)</i>",
                parse_mode="HTML"
            )
            await status_msg.delete()
            return

        # 5. Not in cache -> Download via YouTube (yt-dlp)
        download_result = await download_track_by_query(query)

        if download_result.get("error"):
            await status_msg.edit_text(format_error(download_result, message.from_user.id))
            return

        mp3_path = download_result.get("file_path")
        if not mp3_path or not os.path.exists(mp3_path):
            await status_msg.edit_text("❌ Audio faylni saqlashda xatolik yuz berdi.")
            return

        # Send MP3 to user
        audio_file = FSInputFile(mp3_path, filename=f"{artist} - {title}{os.path.splitext(mp3_path)[1]}")
        sent_audio = await message.reply_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=download_result.get("duration", 0),
            caption=f"🎵 <b>{artist} - {title}</b>",
            parse_mode="HTML"
        )

        # Save to database cache
        if sent_audio.audio:
            await save_track(
                query_key=query,
                title=title,
                artist=artist,
                telegram_file_id=sent_audio.audio.file_id,
                duration=sent_audio.audio.duration or 0
            )

        # Remove local MP3 to save space
        try:
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
        except Exception as e:
            logger.warning("Could not delete local mp3: %s", e)

        await status_msg.delete()

    except Exception as e:
        logger.error("Error in voice handler: %s", e, exc_info=True)
        await status_msg.edit_text("⚠️ Xatolik yuz berdi. Iltimos, birozdan so‘ng qayta urinib ko‘ring.")
    finally:
        # Clean up temp file
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception:
                pass
