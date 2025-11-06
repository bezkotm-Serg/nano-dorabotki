from aiogram import F, Router
from aiogram.types import Message

from storage.credits import add_credits, ensure_user, get_balance
from utils.config import cfg

router = Router()


def _is_admin(uid: int) -> bool:
    return uid in cfg.admin_ids


@router.message(F.text == "/whoami")
async def cmd_whoami(message: Message):
    uid = message.from_user.id
    await message.answer(f"Ваш user_id: {uid}\nСтатус: {'admin' if _is_admin(uid) else 'user'}")


@router.message(F.text == "/reload_admins")
async def cmd_reload_admins(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("Команда доступна только администраторам.")
        return
    import os

    cfg.admin_ids = {
        int(x)
        for x in os.getenv("ADMIN_IDS", "").replace(";", ",").split(",")
        if x.strip().isdigit()
    }
    await message.answer(
        f"ADMIN_IDS перезагружены: {', '.join(map(str, sorted(cfg.admin_ids))) or 'пусто'}"
    )


@router.message(F.text.regexp(r"^/grant(\s+.*)?$"))
async def cmd_grant(message: Message):
    admin_id = message.from_user.id
    if not _is_admin(admin_id):
        await message.answer("Команда доступна только администраторам.")
        return

    target_id = None
    amount = None
    args = (message.text or "").strip().split()

    if message.reply_to_message and len(args) == 2:
        try:
            target_id = message.reply_to_message.from_user.id
            amount = int(args[1])
        except Exception:
            pass

    if target_id is None and len(args) == 3:
        try:
            target_id = int(args[1])
            amount = int(args[2])
        except Exception:
            pass

    if target_id is None or amount is None or amount <= 0:
        await message.answer(
            "Использование:\n• ответьте на сообщение пользователя: `/grant 30`\n• или: `/grant <user_id> <amount>`",
            parse_mode="Markdown",
        )
        return

    ensure_user(target_id, 0)
    add_credits(target_id, amount, reason=f"admin:{admin_id}")
    await message.answer(
        f"Начислено {amount} кредитов пользователю {target_id}. Баланс: {get_balance(target_id)}."
    )
