import os
from datetime import date

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

import fx

app = FastAPI(title="fx-tool")

# ECB serisi 1999-01-04'te başlıyor, öncesi için kur yok.
SERIES_START = date(1999, 1, 4)


@app.exception_handler(fx.FxError)
async def fx_error_handler(request: Request, exc: fx.FxError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": exc.code, "message": exc.message},
    )


@app.get("/tools/convert")
async def convert(
    amount: float = Query(...),
    from_currency: str = Query(..., alias="from"),
    to: str = Query(...),
    asked: date | None = Query(None, alias="date"),
):
    # --- Girdi doğrulama: upstream'e gitmeden elenebilecek her şey ---

    if amount <= 0:
        raise fx.FxError("invalid_amount", "Tutar sıfırdan büyük olmalı.", 400)

    if round(amount, 2) != amount:
        raise fx.FxError(
            "invalid_amount", "Tutar en fazla iki ondalık basamak içerebilir.", 400
        )

    base = from_currency.upper()
    target = to.upper()

    for code in (base, target):
        if len(code) != 3 or not code.isalpha():
            raise fx.FxError(
                "unknown_currency", f"Geçersiz para birimi kodu: {code}.", 400
            )

    today = date.today()
    if asked is not None:
        if asked > today:
            raise fx.FxError(
                "date_out_of_range", "Gelecek bir tarih için kur bulunmuyor.", 400
            )
        if asked < SERIES_START:
            raise fx.FxError(
                "date_out_of_range",
                f"ECB serisi {SERIES_START} tarihinde başlıyor, öncesi için kur yok.",
                400,
            )

    asked_date = asked or today

    # --- Aynı para birimi: kur tanımı gereği 1.0, upstream'e gitmeye gerek yok ---

    if base == target:
        return {
            "amount": amount,
            "from": base,
            "to": target,
            "rate": 1.0,
            "result": round(amount, 2),
            "rate_date": str(asked_date),
            "asked_date": str(asked_date),
            "source": "ECB via frankfurter.dev",
        }

    # --- Upstream ---

    rate, rate_date = await fx.fetch_rate(base, target, asked)

    # Kuru ham haliyle çarp, sadece sonucu yuvarla.
    result = round(amount * rate, 2)

    return {
        "amount": amount,
        "from": base,
        "to": target,
        "rate": rate,
        "result": result,
        "rate_date": rate_date,
        "asked_date": str(asked_date),
        "source": "ECB via frankfurter.dev",
    }