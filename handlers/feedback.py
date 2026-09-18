import html
from config import ADMIN_IDS

DETAIL_LIMIT = 500

_MESSAGES = {
    "not_found": "😔 Hech narsa topilmadi. Qo‘shiq yoki ijrochi nomini to‘g‘ri yozganingizga ishonch hosil qiling.",
    "too_long": "⚠️ Ushbu audio juda uzun. Faqat qisqaroq musiqiy treklarni yuklay olaman.",
    "bot_check": "🚫 YouTube so‘rovni bloklamoqda (bot tekshiruvi). Administrator cookies yoki proxy sozlashi kerak.",
    "unavailable": "❌ Ushbu video mavjud emas yoki yopiq (private).",
    "drm": "🔒 Topilgan yozuvlar DRM bilan himoyalangan (obuna talab qiladi). Boshqa nom bilan qidirib ko‘ring.",
    "network": "🌐 Manba serveriga ulanib bo‘lmadi. Bu ba’zi Instagram havolalarida uchraydi — qo‘shiq nomini yozib qidirib ko‘ring.",
    "download_failed": "❌ Audioni yuklab olishda xatolik yuz berdi.",
}

_DEFAULT_MESSAGE = _MESSAGES["download_failed"]


def format_error(result: dict, user_id: int) -> str:
    """User-facing text for a download error, with the raw yt-dlp detail appended for admins."""
    message = _MESSAGES.get(result.get("error"), _DEFAULT_MESSAGE)
    detail = result.get("detail", "")
    if user_id not in ADMIN_IDS or not detail:
        return message

    escaped = html.escape(detail[:DETAIL_LIMIT])
    return f"{message}\n\n<code>{escaped}</code>"
