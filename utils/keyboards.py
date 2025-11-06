from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Tuple

from utils.config import cfg

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Баланс", callback_data="menu:balance"),
         InlineKeyboardButton(text="➕ Купить кредиты", callback_data="menu:buy")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu:help")],
    ])

def buy_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{c} кредитов — {r}₽", callback_data=f"buy:pack:{c}:{r}")]
            for c, r in cfg.buy_packs]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def scenes_keyboard(scenes: List[List[Tuple[str, str, str]]]) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton(text=f"Все сцены ({len(scenes)}×3)", callback_data="scene:all")])
    for idx, triplet in enumerate(scenes):
        scene_name = triplet[0][0]
        rows.append([InlineKeyboardButton(text=f"{idx + 1}. {scene_name}", callback_data=f"scene:{idx}")])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="scene:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)