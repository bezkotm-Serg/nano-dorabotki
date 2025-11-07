import os
from typing import Final

import httpx

API_BASE: Final[str] = "https://thenewblack.ai/api/1.1/wf"


class TNBError(RuntimeError):
    pass


def _get_auth() -> tuple[str, str]:
    return os.getenv("TNB_EMAIL", "").strip(), os.getenv("TNB_PASSWORD", "").strip()


def _get_default_prompt() -> str:
    return os.getenv("TNB_DEFAULT_PROMPT", "fashion model walking")


def _ensure_auth() -> None:
    email, password = _get_auth()
    if not email or not password:
        raise TNBError("В .env не указаны TNB_EMAIL / TNB_PASSWORD")


def _ensure_url(url: str) -> None:
    if not (url.startswith("http://") or url.startswith("https://")):
        raise TNBError(f"Некорректный URL: {url}")


async def create_variation(image_url: str, prompt: str | None = None) -> str:
    _ensure_auth()
    _ensure_url(image_url)
    email, password = _get_auth()
    prompt = prompt or _get_default_prompt()
    files = {
        "email": (None, email),
        "password": (None, password),
        "image": (None, image_url),
        "prompt": (None, prompt),
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{API_BASE}/variation", files=files)
        if r.status_code >= 400:
            raise TNBError(f"variation [{r.status_code}]: {r.text}")
        result_url = r.text.strip().strip('"').strip()
        if not (result_url.startswith("http://") or result_url.startswith("https://")):
            raise TNBError(f"Не получили URL результата: {r.text}")
        return result_url


async def create_alternative_views(image_url: str, prompt: str | None = None) -> str:
    _ensure_auth()
    _ensure_url(image_url)
    email, password = _get_auth()
    prompt = prompt or _get_default_prompt()
    files = {
        "email": (None, email),
        "password": (None, password),
        "image": (None, image_url),
        "prompt": (None, prompt),
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{API_BASE}/create-alternative-views", files=files)
        if r.status_code >= 400:
            raise TNBError(f"create-alternative-views [{r.status_code}]: {r.text}")
        result_url = r.text.strip().strip('"').strip()
        if not (result_url.startswith("http://") or result_url.startswith("https://")):
            raise TNBError(f"Не получили URL результата: {r.text}")
        return result_url  # <-- фикс: был отсутствующий return
