import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
import httpx


class KIEError(RuntimeError):
    pass


def _get_base() -> str:
    return os.getenv("KIE_API_BASE", "https://api.kie.ai").rstrip("/")


def _get_key() -> str:
    key = os.getenv("KIE_API_KEY", "").strip()
    if not key:
        raise KIEError("В .env не указан KIE_API_KEY")
    return key


def _headers_json() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_defaults() -> Dict[str, Any]:
    return {
        "model": os.getenv("KIE_MODEL", "google/nano-banana-edit"),
        "output_format": os.getenv("KIE_OUTPUT_FORMAT", "") or None,
        "image_size": os.getenv("KIE_IMAGE_SIZE", "") or None,
        "default_prompt": os.getenv("KIE_DEFAULT_PROMPT", "create a close clothing variation"),
    }


async def create_task(
    *,
    prompt: Optional[str],
    image_url: Union[str, None] = None,
    image_urls: Optional[List[str]] = None,
    extra_input: Optional[Dict[str, Any]] = None,
    callback_url: Optional[str] = None,
) -> str:
    """
    Backward-compatible:
    - раньше было image_url: str -> теперь можно image_urls: List[str] (до 10).
    - если передан image_urls, используем его; иначе упакуем одиночный image_url.
    """
    base = _get_base()
    d = _get_defaults()

    urls: List[str] = []
    if image_urls:
        urls = [u for u in image_urls if isinstance(u, str) and u.startswith("http")]
    elif image_url:
        if not image_url.startswith("http"):
            raise KIEError(f"Некорректный image_url: {image_url}")
        urls = [image_url]
    if not urls:
        raise KIEError("Нужен хотя бы один корректный URL изображения")

    input_obj: Dict[str, Any] = {
        "prompt": (prompt or d["default_prompt"]).strip(),
        "image_urls": urls,  # многокадровый ввод
    }
    if d["output_format"]:
        input_obj["output_format"] = d["output_format"]
    if d["image_size"]:
        input_obj["image_size"] = d["image_size"]
    if extra_input:
        input_obj.update(extra_input)

    payload: Dict[str, Any] = {"model": d["model"], "input": input_obj}
    if callback_url:
        payload["callBackUrl"] = callback_url

    url_create = f"{base}/api/v1/jobs/createTask"

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url_create, headers=_headers_json(), json=payload)
                if r.status_code >= 400:
                    raise KIEError(f"createTask [{r.status_code}]: {r.text}")
                data = r.json()
                if data.get("code") != 200:
                    raise KIEError(f"createTask вернул ошибку: {json.dumps(data, ensure_ascii=False)}")
                task_id = (data.get("data") or {}).get("taskId") or ""
                if not task_id:
                    raise KIEError(f"createTask: нет taskId в ответе: {json.dumps(data, ensure_ascii=False)}")
                return task_id
        except Exception as e:
            last_err = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise KIEError(f"Не удалось создать задачу после ретраев: {last_err}")


async def poll_result(task_id: str, *, timeout: int = 600, interval: float = 3.0) -> Dict[str, Any]:
    base = _get_base()
    url = f"{base}/api/v1/jobs/recordInfo"
    deadline = asyncio.get_event_loop().time() + timeout
    last = {}

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            r = await client.get(url, headers={"Authorization": f"Bearer {_get_key()}"}, params={"taskId": task_id})
            if r.status_code >= 400:
                raise KIEError(f"recordInfo [{r.status_code}]: {r.text}")
            data = r.json()
            last = data
            if data.get("code") == 200:
                d = (data.get("data") or {})
                state = (d.get("state") or "").lower()
                if state == "success":
                    return data
                if state == "fail":
                    fail_code = d.get("failCode")
                    fail_msg = d.get("failMsg")
                    param_seen = d.get("param")
                    raise KIEError(f"KIE fail ({fail_code}): {fail_msg}. param={param_seen}")
            if asyncio.get_event_loop().time() > deadline:
                raise KIEError(f"Таймаут ожидания результата: {json.dumps(last, ensure_ascii=False)}")
            await asyncio.sleep(interval)
