from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from database import add_or_update_user

router = Router(name="common_router")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    if user:
        await add_or_update_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"Assalomu alaykum, <b>{user.first_name if user else 'doʻstim'}</b>! 👋\n\n"
        "🎵 <b>Musiqa topuvchi botga xush kelibsiz!</b>\n\n"
        "Bot imkoniyatlari:\n"
        "1. 🎤 <b>Ovoz orqali:</b> Qoʻshiq yangrayotgan ovozli xabar (voice), audio yoki dumaloq video yuboring.\n"
        "2. ✍️ <b>Nomi orqali:</b> Qoʻshiq yoki xonandaning nomini matn qilib yozing.\n"
        "3. 📲 <b>Ijtimoiy tarmoqlar:</b> Instagram Reels, TikTok yoki YouTube Shorts havolasini yuborsangiz, audiosini ajratib beraman.\n"
        "4. ⚡️ <b>Inline rejim:</b> Istalgan chatda <code>@single_music_bot qo'shiq nomi</code> deb yozing!\n\n"
        "Qani, birorta nom yozing yoki havola yuboring! 🎧"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "ℹ️ <b>Botdan foydalanish bo‘yicha to‘liq qo‘llanma:</b>\n\n"
        "• <b>Musiqani eshitib topish:</b> Botga ovozli xabar (voice) yozib jo‘nating (kamida 5-8 soniya).\n"
        "• <b>Qo‘shiq qidirish:</b> Masalan: <code>Konsta Odamlar nima deydi</code>\n"
        "• <b>Instagram / TikTok / Shorts:</b> Video havolasini shunchaki xabarga tashlang, bot uning fon musiqasini MP3 qilib beradi.\n"
        "• <b>Inline qidiruv:</b> Do‘stlaringiz bilan yozishayotganda <code>@single_music_bot trek</code> deb yozsangiz, qo‘shiqlar ro‘yxati chiqadi.\n"
        "• <b>Tezkorlik:</b> Barcha yuklangan qo‘shiqlar keshda saqlanadi va ikkinchi marta darhol yuboriladi."
    )
    await message.answer(help_text, parse_mode="HTML")

