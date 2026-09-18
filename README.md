# Telegram Musiqa Topuvchi Bot (Music Finder Bot)

Ushbu bot ovozli xabar (voice), audio fayl yoki video-xabar orqali qo'shiqlarni **Shazam** yordamida taniy oladi hamda matnli qidiruv orqali MP3 formatda foydalanuvchiga yuklab beradi.

## Imkoniyatlari
- 🎤 **Ovoz orqali qo'shiq topish:** Foydalanuvchi yuborgan audio yoki ovozli xabarni `shazamio` orqali tahlil qilib, ijrochi va qo'shiq nomini aniqlaydi.
- 🔎 **Nomi orqali qidirish:** Qo'shiq yoki san'atkor nomini yozganda `yt-dlp` orqali topib, MP3 formatida yuboradi.
- ⚡️ **Tezkor kesh (SQLite):** Bir marta yuklangan har qanday qo'shiqning Telegram `file_id`si bazaga saqlanadi. Keyingi safar xuddi shu qo'shiq so'ralsa, serverdan qayta yuklab o'tirmasdan, bir zumda jo'natiladi.
- 🧹 **Avtomatik tozalash:** Server diskini to'lib qolmasligi uchun yuklangan vaqtinchalik audio fayllar Telegramga yuborilgach, darhol o'chiriladi.

---

## O'rnatish va Ishga tushirish

### 1. Tizim talabi: FFmpeg
Audioni kesish va MP3 ga aylantirish uchun kompyuteringizda (yoki serverda) `ffmpeg` o'rnatilgan bo'lishi shart:
```bash
# macOS (Homebrew orqali):
brew install ffmpeg

# Ubuntu / Debian serverlarda:
sudo apt update && sudo apt install -y ffmpeg
```

### 2. Virtual muhit va kutubxonalarni o'rnatish
```bash
# Loyiha papkasiga kiring
cd telegram_music_bot

# Virtual muhitni faollashtiring
source venv/bin/activate

# Kutubxonalarni o'rnating
pip install -r requirements.txt
```

### 3. Bot tokenni sozlash
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring va `/newbot` buyrug'i orqali yangi bot oching.
2. Berilgan tokenni nusxalang.
3. Loyihadagi `.env` faylini oching va tokenni kiriting:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 4. Botni ishga tushirish
```bash
python main.py
```

---

## Loyiha Fayllari Tuzilishi
- `main.py` — Botni ishga tushiruvchi asosiy fayl.
- `config.py` — Sozlamalar va yo'llar.
- `database.py` — SQLite asinxron kesh tizimi (`aiosqlite`).
- `services/shazam_service.py` — Musiqani ovozdan aniqlovchi modul (`shazamio`).
- `services/download_service.py` — Qo'shiqni YouTube'dan MP3 qilib yuklovchi modul (`yt-dlp`).
- `handlers/` — Bot komandalari va xabarlar mantiqi:
  - `common.py` — `/start` va `/help` komandalari.
  - `voice_handler.py` — Ovozli va audio xabarlar uchun handler.
  - `search_handler.py` — Matnli qidiruv uchun handler.
