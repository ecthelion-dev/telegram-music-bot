import asyncio
import logging
from aiogram import Router, types, Bot
from aiogram.filters import Command, CommandObject
from config import ADMIN_IDS
from database import get_users_count, get_tracks_count, get_top_tracks, get_all_user_ids
from services.diagnostics import collect_diagnostics, probe_sources

logger = logging.getLogger(__name__)
router = Router(name="admin_router")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("admin", "stats"))
async def cmd_admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return  # Silently ignore non-admins

    users_count = await get_users_count()
    tracks_count = await get_tracks_count()
    top_tracks = await get_top_tracks(limit=5)

    stats_text = (
        "👑 <b>Admin Paneli & Bot Statistikasi</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {users_count} ta\n"
        f"🎧 <b>Bazada saqlangan musiqalar:</b> {tracks_count} ta\n\n"
        "🔥 <b>Eng ko‘p yuklangan Top 5 qo‘shiq:</b>\n"
    )

    if top_tracks:
        for idx, track in enumerate(top_tracks, 1):
            stats_text += f"{idx}. <b>{track.get('artist', '')} - {track.get('title', '')}</b> ({track.get('download_count', 1)} marta)\n"
    else:
        stats_text += "<i>Hozircha musiqalar yuklanmagan</i>\n"

    stats_text += (
        "\n📢 <b>Xabar tarqatish:</b>\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun:\n"
        "<code>/broadcast Sizning xabaringiz</code>\n"
        "yoki istalgan xabarga (rasm, audio, video) <b>Reply</b> qilib <code>/broadcast</code> deb yozing."
    )

    await message.answer(stats_text, parse_mode="HTML")

@router.message(Command("diag"))
async def cmd_diagnostics(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.reply("🔬 Tekshirilmoqda...")
    try:
        report = await collect_diagnostics()
    except Exception as e:
        logger.error("Diagnostics failed: %s", e, exc_info=True)
        await status_msg.edit_text(f"⚠️ Diagnostika bajarilmadi: {e}")
        return

    await status_msg.edit_text(report, parse_mode="HTML")


@router.message(Command("probe"))
async def cmd_probe(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    query = (command.args or "").strip()
    if not query:
        await message.reply(
            "Manbalarni solishtirish uchun: <code>/probe Konsta Sengacha</code>",
            parse_mode="HTML",
        )
        return

    status_msg = await message.reply("🔎 Manbalar tekshirilmoqda...")
    try:
        report = await probe_sources(query)
    except Exception as e:
        logger.error("Probe failed for %r: %s", query, e, exc_info=True)
        await status_msg.edit_text(f"⚠️ Tekshiruv bajarilmadi: {e}")
        return

    await status_msg.edit_text(report, parse_mode="HTML")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    # Determine message to broadcast
    reply_msg = message.reply_to_message
    broadcast_text = message.text.replace("/broadcast", "", 1).strip()

    if not reply_msg and not broadcast_text:
        await message.reply(
            "⚠️ <b>Qanday xabar tarqatish kerak?</b>\n\n"
            "1. Oddiy matn uchun: <code>/broadcast Assalomu alaykum...</code>\n"
            "2. Rasm/video/audio uchun: Xabarga <b>Reply</b> qilib <code>/broadcast</code> deb yuboring.",
            parse_mode="HTML"
        )
        return

    user_ids = await get_all_user_ids()
    total = len(user_ids)
    if total == 0:
        await message.reply("Bazadagi foydalanuvchilar topilmadi.")
        return

    progress_msg = await message.reply(f"🚀 Xabar tarqatish boshlandi... Jami qabul qiluvchilar: {total} ta")

    success_count = 0
    blocked_count = 0

    for uid in user_ids:
        try:
            if reply_msg:
                # Forward or copy the exact replied message
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=reply_msg.message_id
                )
            else:
                await bot.send_message(chat_id=uid, text=broadcast_text, parse_mode="HTML")
            
            success_count += 1
            await asyncio.sleep(0.05)  # Avoid Telegram FloodWait limit (30 msgs/sec)
        except Exception as e:
            logger.warning("Failed to send broadcast to %s: %s", uid, e)
            blocked_count += 1

    await progress_msg.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"👥 Jami: {total} ta\n"
        f"🟢 Yetkazildi: {success_count} ta\n"
        f"🔴 Yetkazilmadi (botni bloklagan): {blocked_count} ta",
        parse_mode="HTML"
    )
