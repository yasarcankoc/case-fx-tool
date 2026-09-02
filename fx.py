import os
from datetime import date

import httpx


UPSTREAM_BASE = os.getenv("FX_UPSTREAM_BASE", "https://api.frankfurter.dev")
TIMEOUT_SECONDS = 5.0


class FxError(Exception):
    """Upstream veya girdi kaynaklı, istemciye dönülecek hata."""

    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)
        
        
_cache: dict[tuple[str, str, str], tuple[float, str]] = {}


async def fetch_rate(base: str, target: str, on: date | None) -> tuple[float, str]:
    """Kuru ve kurun gerçekten ait olduğu tarihi döndürür."""
    if on is not None:
        key = (base, target, str(on))
        if key in _cache:
            return _cache[key]

    path = str(on) if on else "latest"
    url = f"{UPSTREAM_BASE}/v1/{path}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, params={"base": base, "symbols": target})
    except httpx.RequestError:
        raise FxError("upstream_unavailable", "Kur servisine ulaşılamadı.", 502)

    if response.status_code == 404:
        raise FxError("unknown_currency", f"Bilinmeyen para birimi: {base} veya {target}.", 400)

    if response.status_code >= 400:
        raise FxError("upstream_unavailable", "Kur servisi şu anda cevap veremiyor.", 502)

    try:
        payload = response.json()
    except ValueError:
        raise FxError("upstream_invalid_response", "Kur servisinden geçersiz cevap alındı.", 502)

    rates = payload.get("rates")
    rate_date = payload.get("date")
    if not isinstance(rates, dict) or not isinstance(rate_date, str):
        raise FxError("upstream_invalid_response", "Kur servisinin cevabı beklenen biçimde değil.", 502)

    if target not in rates:
        raise FxError("unknown_currency", f"Bilinmeyen para birimi: {target}.", 400)

    rate = float(rates[target])

    if on is not None:
        _cache[(base, target, str(on))] = (rate, rate_date)

    return rate, rate_date