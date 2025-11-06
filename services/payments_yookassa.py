# path: services/payments_yookassa.py
import os
from typing import Any

from yookassa import Configuration, Payment
from yookassa.domain.exceptions.api_error import ApiError


def _env() -> dict[str, str]:
    return {
        "shop_id": os.getenv("YK_SHOP_ID", "").strip(),
        "secret": os.getenv("YK_SECRET", "").strip(),
        "currency": os.getenv("CURRENCY", "RUB").strip(),
        "vat_code": os.getenv("RECEIPT_VAT_CODE", "1").strip(),  # 1 = без НДС по умолчанию
    }


def is_enabled() -> bool:
    e = _env()
    return bool(e["shop_id"] and e["secret"])


def _configure():
    e = _env()
    if not (e["shop_id"] and e["secret"]):
        raise RuntimeError("YooKassa disabled: YK_SHOP_ID / YK_SECRET не заданы в .env")
    Configuration.account_id = e["shop_id"]
    Configuration.secret_key = e["secret"]
    return e


def _build_receipt(amount_value: str, cfg: dict[str, str], user_id: int) -> dict[str, Any]:
    """
    Минимальный корректный чек для цифровых услуг:
    - payment_subject='service'
    - payment_mode='full_prepayment'
    - vat_code из ENV (по умолчанию 1 — без НДС)
    """
    return {
        "customer": {
            "full_name": f"tg-{user_id}",
            "email": "no-reply@example.com",  # хотя бы email или phone обязателен
        },
        "items": [
            {
                "description": "Credits pack",
                "quantity": "1.0",
                "amount": {"value": amount_value, "currency": cfg["currency"]},
                "vat_code": int(cfg["vat_code"]),
                "payment_subject": "service",
                "payment_mode": "full_prepayment",
            }
        ],
    }


def create_payment(user_id: int, credits: int, amount_rub: int) -> tuple[str, str]:
    """Создаёт платёж. Возвращает (payment_id, confirmation_url)."""
    cfg = _configure()
    amount_value = f"{float(amount_rub):.2f}"
    payload = {
        "amount": {"value": amount_value, "currency": cfg["currency"]},
        "capture": True,
        "description": f"TG:{user_id} • {credits} credits",
        "confirmation": {"type": "redirect", "return_url": "https://t.me"},
        "metadata": {"user_id": user_id, "credits": credits},
        "receipt": _build_receipt(amount_value, cfg, user_id),
    }
    try:
        resp = Payment.create(payload)
        return resp.id, resp.confirmation.confirmation_url
    except ApiError as e:
        details = getattr(e, "response", None) or {}
        message = getattr(e, "message", str(e))
        code = getattr(e, "code", "api_error")
        raise RuntimeError(f"{code}: {message} | details={details}") from e
    except Exception as e:
        raise RuntimeError(f"transport_error: {e!s}") from e


def get_payment_status(payment_id: str) -> str:
    _configure()
    try:
        p = Payment.find_one(payment_id)
        return p.status  # pending | waiting_for_capture | succeeded | canceled
    except ApiError as e:
        details = getattr(e, "response", None) or {}
        message = getattr(e, "message", str(e))
        code = getattr(e, "code", "api_error")
        raise RuntimeError(f"{code}: {message} | details={details}") from e
