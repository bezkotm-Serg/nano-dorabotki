import os
from dataclasses import dataclass
from typing import Final


DEFAULT_BUY_PACKS: Final[list[tuple[int, int]]] = [(30, 149), (120, 399), (350, 899)]


def _parse_admins(env: str) -> set[int]:
    ids: set[int] = set()
    for p in (env or "").replace(";", ",").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            ids.add(int(p))
        except ValueError:
            pass
    return ids


def _parse_buy_packs(env: str) -> list[tuple[int, int]]:
    res: list[tuple[int, int]] = []
    for item in (env or "").split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 2:
            continue
        try:
            c, r = int(parts[0]), int(parts[1])
            if c > 0 and r > 0:
                res.append((c, r))
        except ValueError:
            continue
    return res or DEFAULT_BUY_PACKS


@dataclass
class Config:
    # базовые
    mode: str = "REAL"
    feature: str = "KIE_IMAGE"

    # bot
    bot_token: str = ""
    admin_ids: set[int] = None

    # поведение/промпты
    use_caption_as_prompt: bool = True
    show_prompt_in_caption: bool = False
    default_prompt: str = "create a close clothing variation"
    tnb_default_prompt: str = "fashion model walking"
    kie_scenes_limit: int = 7

    # платежи/кредиты
    welcome_credits: int = 5
    buy_packs: list[tuple[int, int]] = None
    currency: str = "RUB"

    # скрытое состояние (ENV прочитан?)
    _loaded: bool = False

    def reload(self) -> None:
        self.mode = os.getenv("MODE", "REAL").upper()
        self.feature = os.getenv("TNB_FEATURE", "KIE_IMAGE").upper()

        self.bot_token = os.getenv("BOT_TOKEN", "").strip()
        self.admin_ids = _parse_admins(os.getenv("ADMIN_IDS", ""))

        self.use_caption_as_prompt = os.getenv("USE_CAPTION_AS_PROMPT", "1") == "1"
        self.show_prompt_in_caption = os.getenv("SHOW_PROMPT_IN_CAPTION", "0") == "1"
        self.default_prompt = os.getenv("KIE_DEFAULT_PROMPT", self.default_prompt)
        self.tnb_default_prompt = os.getenv("TNB_DEFAULT_PROMPT", self.tnb_default_prompt)
        try:
            self.kie_scenes_limit = int(os.getenv("KIE_SCENES_LIMIT", "7"))
        except ValueError:
            self.kie_scenes_limit = 7

        try:
            self.welcome_credits = int(os.getenv("WELCOME_CREDITS", "5"))
        except ValueError:
            self.welcome_credits = 5
        self.buy_packs = _parse_buy_packs(os.getenv("BUY_PACKS", "30:149,120:399,350:899"))
        self.currency = os.getenv("CURRENCY", "RUB")

        self._loaded = True


cfg = Config()
# Важно: main вызывает cfg.reload() после load_dotenv()
