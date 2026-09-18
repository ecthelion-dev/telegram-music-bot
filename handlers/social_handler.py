import os
import re
import logging
from aiogram import Router, types, F, Bot
from aiogram.types import FSInputFile
from aiogram.enums import ChatAction
from services.download_service import download_social_media_audio
from database import save_track, get_cached_track

logger = logging.getLogger(__name__)
router = Router(name="social_router")

# Regex pattern for Instagram, TikTok, YouTube Shorts / videos
URL_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:instagram\.com/(?:reel|p|tv)/|tiktok\.com/|vm\.tiktok\.com/|youtube\.com/shorts/|youtu\.be/|youtube\.com/watch\?v=)[^\s]+)",
    re.IGNORECASE
)

@router.message(F.text.regexp(URL_REGEX))
async def handle_social_media_link(message: types.Message, bot: Bot):
    text = message.text.strip()
    match = URL_REGEX.search(text)
    if not match:
        return

    url = match.group(1)
    status_msg = await message.reply("📥 Havola qabul qilindi. Fon musiqasi yuklab olinmoqda... ⏳")
    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)

    # Check cache first using URL as key
    cached = await get_cached_track(url)
    if cached and cached.get("telegram_file_id"):
        await message.reply_audio(
            audio=cached["telegram_file_id"],
            caption=f"🎵 <b>{cached.get('artist', '')} - {cached.get('title', '')}</b>\n<i>(Tezkor keshdan yuborildi)</i>",
            parse_mode="HTML"
        )
        await status_msg.delete()
        return

    try:
        result = await download_social_media_audio(url)
        if not result or not result.get("file_path"):
            await status_msg.edit_text("❌ Ushbu havoladan audioni ajratib olib bo‘lmadi. Havola ochiq (public) ekanligiga ishonch hosil qiling.")
            return

        mp3_path = result["file_path"]
        if not os.path.exists(mp3_path):
            await status_msg.edit_text("❌ Audio faylni saqlashda xatolik yuz berdi.")
            return

        title = result.get("title", "Audio trek")
        artist = result.get("artist", "")
        duration = result.get("duration", 0)

        audio_file = FSInputFile(mp3_path, filename=f"{title}.mp3")
        sent_audio = await message.reply_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=duration,
            caption=f"🎧 <b>{title}</b>\n🔗 <a href='{url}'>Manba havolasi</a>",
            parse_mode="HTML"
        )

        # Cache in database
        if sent_audio.audio:
            await save_track(
                query_key=url,
                title=title,
                artist=artist,
                telegram_file_id=sent_audio.audio.file_id,
                duration=sent_audio.audio.duration or duration
            )

        # Remove local file
        try:
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
        except Exception as e:
            logger.warning("Could not delete social mp3: %s", e)

        await status_msg.delete()

    except Exception as e:
        logger.error("Error in social media link handler: %s", e, exc_info=True)
        await status_msg.edit_text("⚠️ Havolani qayta ishlashda xatolik yuz berdi.")
