import logging
from aiogram import Router, types
from aiogram.types import InlineQueryResultCachedAudio, InlineQueryResultArticle, InputTextMessageContent
from database import search_cached_tracks, get_top_tracks

logger = logging.getLogger(__name__)
router = Router(name="inline_router")

@router.inline_query()
async def handle_inline_music_search(inline_query: types.InlineQuery):
    query = inline_query.query.strip()
    results = []

    if not query:
        # If no query, show top/recent tracks from cache
        top_tracks = await get_top_tracks(limit=10)
        # We can also get cached tracks with telegram_file_id
        cached_tracks = await search_cached_tracks("", limit=10)
        
        for idx, track in enumerate(cached_tracks):
            if track.get("telegram_file_id"):
                results.append(
                    InlineQueryResultCachedAudio(
                        id=f"cached_{track['id']}_{idx}",
                        audio_file_id=track["telegram_file_id"],
                        caption=f"🎵 <b>{track.get('artist', '')} - {track.get('title', '')}</b>\nvia @single_music_bot",
                        parse_mode="HTML"
                    )
                )
    else:
        # Search cached tracks first
        cached_matches = await search_cached_tracks(query, limit=10)
        for idx, track in enumerate(cached_matches):
            if track.get("telegram_file_id"):
                results.append(
                    InlineQueryResultCachedAudio(
                        id=f"match_{track['id']}_{idx}",
                        audio_file_id=track["telegram_file_id"],
                        caption=f"🎵 <b>{track.get('artist', '')} - {track.get('title', '')}</b>\nvia @single_music_bot",
                        parse_mode="HTML"
                    )
                )

        # If no results found in cache, show informative tip to open bot
        if not results:
            results.append(
                InlineQueryResultArticle(
                    id="not_found",
                    title=f"'{query}' bo‘yicha musiqa topilmadi",
                    description="Botga o‘tib to‘liq qidirish yoki ovoz yuborish uchun bu yerni bosing",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🎵 Men @single_music_bot orqali <b>{query}</b> qo‘shig‘ini qidirmoqdaman!",
                        parse_mode="HTML"
                    )
                )
            )

    await inline_query.answer(
        results=results,
        cache_time=5,
        is_personal=True
    )
