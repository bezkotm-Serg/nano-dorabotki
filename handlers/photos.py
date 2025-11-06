import asyncio
import logging
from typing import List, Tuple, Dict

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message

from services.presets import build_presets
from utils.config import cfg
from utils.keyboards import scenes_keyboard
from storage.credits import get_balance, spend_credits
from storage.files import TEMP_DIR
from services.video_pipeline import run_kie_from_telegram_file, run_kie_from_telegram_files
from handlers.common import GLOBAL_LAST_PHOTO  # общий кэш последнего фото
from handlers.common import _clip, _chunk_scenes

router = Router()
log = logging.getLogger("photos")

# Кэш для альбомов: media_group_id -> list[file_path]
_ALBUM_CACHE: Dict[str, List[str]] = {}

@router.message(F.photo & F.media_group_id.as_("gid"))
async def handle_album_part(message: Message, gid: str):
    """
    Собираем элементы альбома в кэш и через короткую задержку
    обрабатываем всю группу единым таском KIE (до 10 фото).
    """
    try:
        photo = message.photo[-1]
        tg_file = await message.bot.get_file(photo.file_id)
        _ALBUM_CACHE.setdefault(gid, []).append(tg_file.file_path)

        # Первый элемент — планируем обработку через ~1 секунду
        if len(_ALBUM_CACHE[gid]) == 1:
            async def _flush_after_delay():
                await asyncio.sleep(1.2)  # простая эвристика завершения группы
                paths = _ALBUM_CACHE.pop(gid, [])
                if not paths:
                    return
                user_id = message.from_user.id
                if get_balance(user_id) < 1:
                    await message.answer("Нужен 1 кредит для генерации альбома. /buy — пополнить.")
                    return
                try:
                    out_path = await run_kie_from_telegram_files(
                        bot_token=cfg.bot_token, tg_file_paths=paths, out_dir=TEMP_DIR,
                        prompt=(message.caption or "").strip() or None
                    )
                    await message.answer_photo(
                        photo=FSInputFile(str(out_path)),
                        caption=("Готово ✅\nальбом + промпт: " + _clip((message.caption or ""), 200))
                        if cfg.show_prompt_in_caption and message.caption else "Готово ✅"
                    )
                    spend_credits(user_id, 1)  # 1 задача = 1 кредит
                except Exception as e:
                    log.exception("Album failed: %s", e)
                    await message.answer(f"Ошибка генерации по альбому: {e}")
            asyncio.create_task(_flush_after_delay())
    except Exception as e:
        log.exception("Album collect error: %s", e)

@router.callback_query(F.data.startswith("scene:"))
async def on_scene_choice(callback: CallbackQuery):
    try:
        user_id = callback.from_user.id
        tg_file_path = GLOBAL_LAST_PHOTO.get(user_id)
        if not tg_file_path:
            await callback.answer("Сначала пришли фото.", show_alert=True)
            return

        presets = build_presets()
        scenes = _chunk_scenes(presets)
        choice = callback.data.split(":", 1)[1]

        if choice == "cancel":
            GLOBAL_LAST_PHOTO.pop(user_id, None)
            await callback.message.edit_text("Отменено.")
            return

        if choice == "all":
            chosen = scenes[: max(1, min(cfg.kie_scenes_limit, len(scenes)))]
            title = f"Все сцены ({len(chosen)}×3)"
        else:
            idx = int(choice)
            if not (0 <= idx < len(scenes)):
                await callback.answer("Некорректный номер сцены.", show_alert=True)
                return
            chosen = [scenes[idx]]
            title = f"Сцена: {scenes[idx][0][0]}"

        total_needed = 3 * len(chosen)
        bal = get_balance(user_id)
        if bal < total_needed:
            await callback.message.edit_text(f"Нужно {total_needed} кредитов, у тебя {bal}. Нажми /buy, чтобы пополнить.")
            return

        try:
            await callback.message.edit_text(f"Генерация: {title}…")
        except TelegramBadRequest:
            pass
        await callback.answer()

        sent = 0
        for triplet in chosen:
            for scene, shot, ptxt in triplet:
                try:
                    out_path = await run_kie_from_telegram_file(
                        bot_token=cfg.bot_token, tg_file_path=tg_file_path, out_dir=TEMP_DIR, prompt=ptxt
                    )
                    cap = f"{scene} • {shot}\n{_clip(ptxt, 300)}" if cfg.show_prompt_in_caption else f"{scene} • {shot}"
                    await callback.message.answer_photo(photo=FSInputFile(str(out_path)), caption=cap)
                    spend_credits(user_id, 1)
                    sent += 1
                except Exception as e:
                    log.exception("Preset failed: %s | %s: %s", scene, shot, e)
                    await callback.message.answer(f"Сбой: {scene} • {shot}\n— {e}")

        GLOBAL_LAST_PHOTO.pop(user_id, None)

        if sent == 0:
            await callback.message.answer("Не удалось сгенерировать ни один вариант.")
        else:
            await callback.message.answer(f"Готово ✅ Отправлено: {sent}. Баланс: {get_balance(user_id)}")

    except Exception as e:
        log.exception("Ошибка меню: %s", e)
        await callback.message.answer("Ошибка. Попробуй ещё раз.")