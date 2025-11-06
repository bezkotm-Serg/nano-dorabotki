# path: handlers/common.py
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from services.payments_yookassa import create_payment, get_payment_status, is_enabled as yk_enabled
from services.presets import build_presets
from services.video_pipeline import (
    run_kie_from_telegram_file,  # KIE нужен всегда
    run_mock_pipeline,
)
from storage.credits import (
    add_credits,
    ensure_user,
    get_balance,
    mark_payment_applied,
    register_payment,
    set_payment_status,
)
from storage.files import TEMP_DIR, ensure_dirs
from utils.config import cfg
from utils.keyboards import buy_keyboard, main_menu_kb, scenes_keyboard

log = logging.getLogger("common")
router = Router()
GLOBAL_LAST_PHOTO: dict[int, str] = {}


def _clip(text: str, limit: int = 220) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else t[: limit - 1] + "…"


def _chunk_scenes(presets: list[tuple[str, str, str]]) -> list[list[tuple[str, str, str]]]:
    return [presets[i : i + 3] for i in range(0, len(presets), 3)]


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    is_new, balance = ensure_user(message.from_user.id, cfg.welcome_credits)
    welcome = (
        "👋 Привет! Я помогу быстро собрать набор кадров по сценам.\n\n"
        "1) Пришли одно фото.\n"
        "2) Выбери группу сцен (3 ракурса) или укажи промпт подписью к фото.\n"
        "3) За каждый сгенерированный кадр списывается 1 кредит."
    )
    bonus = (
        f"\n\n🎁 Новым пользователям начисляем {cfg.welcome_credits} бонусных кредитов."
        if is_new and cfg.welcome_credits > 0
        else ""
    )
    tail = f"\n\nТвой баланс: {balance} кредитов."
    await message.answer(welcome + bonus + tail, reply_markup=main_menu_kb())


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    txt = (
        "ℹ️ Справка\n\n"
        "• Фото без подписи — выберешь сцену (3 кадра).\n"
        "• Фото с подписью — 1 кадр по промпту.\n"
        "• /balance — баланс\n"
        "• /buy — купить кредиты\n"
        "• 1 кадр = 1 кредит\n"
    )
    if message.from_user.id in cfg.admin_ids:
        txt += (
            "\nАдмин:\n• /grant <user_id> <amount> — начислить кредиты (или ответьте на сообщение пользователя: "
            "`/grant <amount>`)."
        )
    await message.answer(txt)


@router.message(F.text == "/balance")
async def cmd_balance(message: Message):
    await message.answer(f"Баланс: {get_balance(message.from_user.id)} кредитов.")


@router.message(F.text == "/buy")
async def cmd_buy(message: Message):
    if not yk_enabled():
        await message.answer("Оплата недоступна: не настроены YK_SHOP_ID / YK_SECRET в .env")
        return
    await message.answer("Выбери пакет кредитов:", reply_markup=buy_keyboard())


@router.message(F.text == "/ykdiag")
async def cmd_ykdiag(message: Message):
    if not yk_enabled():
        await message.answer("YK не настроена: нет YK_SHOP_ID/YK_SECRET в .env (корень проекта).")
        return
    try:
        pid, url = create_payment(message.from_user.id, credits=1, amount_rub=1)
        await message.answer(
            f"YooKassa OK. payment_id: {pid}\nurl: {url}\n(тест, можно не оплачивать)"
        )
    except Exception as e:
        log.exception("YK diag failed: %s", e)
        await message.answer(f"YooKassa ERROR: {str(e)[:900]}")


@router.callback_query(F.data == "menu:balance")
async def menu_balance(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(f"Баланс: {get_balance(callback.from_user.id)} кредитов.")


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery):
    await callback.answer()
    if not yk_enabled():
        await callback.message.answer(
            "Оплата недоступна: не настроены YK_SHOP_ID / YK_SECRET в .env"
        )
        return
    await callback.message.answer("Выбери пакет кредитов:", reply_markup=buy_keyboard())


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)


@router.callback_query(F.data.startswith("buy:pack:"))
async def on_buy_pack(callback: CallbackQuery):
    _, _, c, r = callback.data.split(":")
    credits, rub = int(c), int(r)
    try:
        pid, url = create_payment(callback.from_user.id, credits, rub)
    except Exception as e:
        log.exception("YooKassa create_payment failed: %s", e)
        await callback.answer("Не удалось создать платёж.", show_alert=True)
        await callback.message.answer(f"Ошибка платёжного провайдера: {str(e)[:400]}")
        return

    register_payment(pid, callback.from_user.id, credits, rub * 100, cfg.currency)
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", url=url)],
            [InlineKeyboardButton(text="Проверить оплату", callback_data=f"buy:check:{pid}")],
        ]
    )
    await callback.message.answer(
        f"Пакет: {credits} кредитов за {rub}₽.\nПосле оплаты нажми «Проверить оплату».",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:check:"))
async def on_buy_check(callback: CallbackQuery):
    pid = callback.data.split(":")[-1]
    try:
        status = get_payment_status(pid)
    except Exception as e:
        log.exception("YooKassa status failed: %s", e)
        await callback.message.answer(f"Не удалось проверить статус платежа: {str(e)[:400]}")
        await callback.answer()
        return

    if status in ("succeeded", "waiting_for_capture"):
        applied = mark_payment_applied(pid)
        if applied:
            user_id, credits = applied
            add_credits(user_id, credits, reason=f"yookassa:{pid}")
            await callback.message.answer(
                f"Оплата подтверждена ✅. Начислено {credits} кредитов.\nБаланс: {get_balance(user_id)}."
            )
        else:
            await callback.message.answer("Этот платёж уже применён ✅")
    elif status == "pending":
        await callback.message.answer(
            "Платёж ещё не завершён. Заверши оплату и нажми «Проверить оплату»."
        )
    elif status == "canceled":
        set_payment_status(pid, "canceled")
        await callback.message.answer("Платёж отменён.")
    else:
        await callback.message.answer(f"Статус платежа: {status}")
    await callback.answer()


@router.message(F.photo)
async def handle_photo(message: Message):
    ensure_user(message.from_user.id, cfg.welcome_credits)
    try:
        ensure_dirs()
        photo = message.photo[-1]
        tg_file = await message.bot.get_file(photo.file_id)
        tg_file_path = tg_file.file_path
        caption = (message.caption or "").strip()
        user_id = message.from_user.id

        # MOCK
        if cfg.mode == "MOCK":
            out_path = await run_mock_pipeline(Path(), TEMP_DIR)
            await message.answer_video(video=FSInputFile(str(out_path)), caption="Готово ✅")
            return

        # TNB режимы — ленивые импорты, чтобы избежать ImportError при KIE_ONLY
        if cfg.feature in ("VARIATION", "ALT_VIEWS"):
            if get_balance(user_id) < 1:
                await message.answer("Не хватает кредитов. Команда /buy — пополнить.")
                return
            from services.video_pipeline import (
                run_altviews_from_telegram_file,
                run_variation_from_telegram_file,
            )

            prompt = caption if (cfg.use_caption_as_prompt and caption) else cfg.tnb_default_prompt
            runner = (
                run_variation_from_telegram_file
                if cfg.feature == "VARIATION"
                else run_altviews_from_telegram_file
            )
            out_path = await runner(
                bot_token=cfg.bot_token, tg_file_path=tg_file_path, out_dir=TEMP_DIR, prompt=prompt
            )
            await message.answer_photo(
                photo=FSInputFile(str(out_path)),
                caption=(
                    f"Готово ✅\nprompt: {_clip(prompt)}"
                    if cfg.show_prompt_in_caption
                    else "Готово ✅"
                ),
            )
            from storage.credits import spend_credits

            spend_credits(user_id, 1)
            return

        # KIE режим
        if cfg.feature == "KIE_IMAGE":
            if caption and cfg.use_caption_as_prompt:
                from storage.credits import spend_credits

                if get_balance(user_id) < 1:
                    await message.answer("Нужен 1 кредит для генерации. /buy — пополнить.")
                    return
                out_path = await run_kie_from_telegram_file(
                    bot_token=cfg.bot_token,
                    tg_file_path=tg_file_path,
                    out_dir=TEMP_DIR,
                    prompt=caption,
                )
                await message.answer_photo(
                    photo=FSInputFile(str(out_path)),
                    caption=(
                        f"Готово ✅\nprompt: {_clip(caption)}"
                        if cfg.show_prompt_in_caption
                        else "Готово ✅"
                    ),
                )
                spend_credits(user_id, 1)
                return

            presets: list[tuple[str, str, str]] = build_presets()
            scenes = _chunk_scenes(presets)
            GLOBAL_LAST_PHOTO[user_id] = tg_file_path
            await message.answer(
                "Выбери группу сцен для генерации (каждая сцена содержит 3 ракурса):",
                reply_markup=scenes_keyboard(scenes),
            )
            return

        await message.answer(
            "Неизвестная фича. Укажи TNB_FEATURE=VARIATION / ALT_VIEWS / KIE_IMAGE в .env"
        )

    except Exception as e:
        log.exception("Ошибка при обработке фото: %s", e)
        await message.answer("Ошибка. Проверь конфиг и логи.")
