from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from services.kie_client import KIEError, create_task, poll_result

# why: TNB функции требуются handlers/common.py при FEATURE=VARIATION/ALT_VIEWS
from services.the_new_black_client import create_alternative_views, create_variation


def build_telegram_file_url(bot_token: str, file_path: str) -> str:
    """Build direct URL to Telegram file content."""
    return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"


async def _download(url: str, out_path: Path) -> Path:
    """Download result to disk; create parent dirs if needed."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.get(url)
        r.raise_for_status()
        out_path.write_bytes(r.content)
    return out_path


# -----------------------------
# MOCK pipeline (for local demo)
# -----------------------------
async def run_mock_pipeline(input_path: Path, out_dir: Path) -> Path:
    demo = Path("temp/demo_result.mp4")
    if not demo.exists():
        raise FileNotFoundError("Place temp/demo_result.mp4 for MOCK mode.")
    await asyncio.sleep(2)
    return demo


# -----------------------------
# TNB (thenewblack.ai) helpers
# -----------------------------
async def run_variation_from_telegram_file(
    *,
    bot_token: str,
    tg_file_path: str,
    out_dir: Path,
    prompt: str | None = None,
) -> Path:
    """Generate single-image variation via TNB."""
    image_url = build_telegram_file_url(bot_token, tg_file_path)
    result_url = await create_variation(image_url=image_url, prompt=prompt)

    low = result_url.lower()
    ext = ".png" if low.endswith(".png") else (".jpeg" if low.endswith(".jpeg") else ".jpg")
    out_path = out_dir / f"tnb_variation_{Path(tg_file_path).stem}{ext}"
    return await _download(result_url, out_path)


async def run_altviews_from_telegram_file(
    *,
    bot_token: str,
    tg_file_path: str,
    out_dir: Path,
    prompt: str | None = None,
) -> Path:
    """Generate alternative views via TNB."""
    image_url = build_telegram_file_url(bot_token, tg_file_path)
    result_url = await create_alternative_views(image_url=image_url, prompt=prompt)

    low = result_url.lower()
    ext = ".png" if low.endswith(".png") else (".jpeg" if low.endswith(".jpeg") else ".jpg")
    out_path = out_dir / f"tnb_altviews_{Path(tg_file_path).stem}{ext}"
    return await _download(result_url, out_path)


# -----------------------------
# KIE (nano-banana-edit)
# -----------------------------
async def _choose_ext(url: str) -> str:
    low = url.lower()
    if low.endswith(".jpg"):
        return ".jpg"
    if low.endswith(".jpeg"):
        return ".jpeg"
    return ".png"


async def run_kie_from_telegram_file(
    *,
    bot_token: str,
    tg_file_path: str,
    out_dir: Path,
    prompt: str | None = None,
    extra_input: dict | None = None,
) -> Path:
    """KIE single-image edit."""
    image_url = build_telegram_file_url(bot_token, tg_file_path)
    task_id = await create_task(prompt=prompt, image_url=image_url, extra_input=extra_input)
    rec = await poll_result(task_id, timeout=600, interval=3.0)

    data = rec.get("data") or {}
    result_json_str = data.get("resultJson") or ""
    if not result_json_str:
        raise KIEError(f"recordInfo: empty resultJson: {rec}")

    try:
        result_obj = json.loads(result_json_str)
    except Exception as e:
        raise KIEError(f"recordInfo: bad resultJson: {result_json_str}") from e

    urls = result_obj.get("resultUrls") or []
    if not urls:
        raise KIEError(f"recordInfo: no resultUrls in {result_obj}")

    result_url = urls[0]
    out_path = out_dir / f"kie_{Path(tg_file_path).stem}{await _choose_ext(result_url)}"
    return await _download(result_url, out_path)


async def run_kie_from_telegram_files(
    *,
    bot_token: str,
    tg_file_paths: list[str],
    out_dir: Path,
    prompt: str | None = None,
    extra_input: dict | None = None,
) -> Path:
    """KIE multi-image edit (up to 10 input images in one task)."""
    if not tg_file_paths:
        throw = KIEError("Empty input list")
        raise throw

    urls_in = [build_telegram_file_url(bot_token, p) for p in tg_file_paths][:10]
    task_id = await create_task(prompt=prompt, image_urls=urls_in, extra_input=extra_input)
    rec = await poll_result(task_id, timeout=600, interval=3.0)

    data = rec.get("data") or {}
    result_json_str = data.get("resultJson") or ""
    if not result_json_str:
        raise KIEError(f"recordInfo: empty resultJson: {rec}")

    try:
        result_obj = json.loads(result_json_str)
    except Exception as e:
        raise KIEError(f"recordInfo: bad resultJson: {result_json_str}") from e

    urls_out = result_obj.get("resultUrls") or []
    if not urls_out:
        raise KIEError(f"recordInfo: no resultUrls in {result_obj}")

    result_url = urls_out[0]
    out_path = out_dir / f"kie_album_{Path(tg_file_paths[0]).stem}{await _choose_ext(result_url)}"
    return await _download(result_url, out_path)
