import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import app as app_module
import fx

client = TestClient(app_module.app)

BASE = fx.UPSTREAM_BASE


@pytest.fixture(autouse=True)
def clear_cache():
    """Her test temiz cache ile başlasın."""
    fx._cache.clear()


@respx.mock
def test_successful_conversion():
    respx.get(f"{BASE}/v1/2026-08-28").mock(
        return_value=httpx.Response(
            200,
            json={"amount": 1.0, "base": "EUR", "date": "2026-08-28",
                  "rates": {"TRY": 47.1234}},
        )
    )

    response = client.get(
        "/tools/convert",
        params={"amount": 250, "from": "EUR", "to": "TRY", "date": "2026-08-28"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rate"] == 47.1234
    assert body["result"] == 11780.85
    assert body["rate_date"] == "2026-08-28"
    assert body["asked_date"] == "2026-08-28"


@respx.mock
def test_weekend_returns_earlier_rate_date():
    # 29 Ağustos cumartesi; ECB cuma kurunu döndürür.
    respx.get(f"{BASE}/v1/2026-08-29").mock(
        return_value=httpx.Response(
            200,
            json={"amount": 1.0, "base": "EUR", "date": "2026-08-28",
                  "rates": {"TRY": 47.1234}},
        )
    )

    response = client.get(
        "/tools/convert",
        params={"amount": 250, "from": "EUR", "to": "TRY", "date": "2026-08-29"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["asked_date"] == "2026-08-29"
    assert body["rate_date"] == "2026-08-28"


@respx.mock
def test_unknown_currency_returns_400():
    respx.get(f"{BASE}/v1/latest").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )

    response = client.get(
        "/tools/convert",
        params={"amount": 100, "from": "EUR", "to": "XYZ"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unknown_currency"


def test_negative_amount_returns_400():
    response = client.get(
        "/tools/convert",
        params={"amount": -5, "from": "EUR", "to": "TRY"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_amount"


def test_future_date_returns_400():
    response = client.get(
        "/tools/convert",
        params={"amount": 100, "from": "EUR", "to": "TRY", "date": "2030-01-01"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "date_out_of_range"


@respx.mock
def test_upstream_500_returns_502():
    respx.get(f"{BASE}/v1/latest").mock(return_value=httpx.Response(500))

    response = client.get(
        "/tools/convert",
        params={"amount": 100, "from": "EUR", "to": "TRY"},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "upstream_unavailable"


@respx.mock
def test_non_json_upstream_returns_502():
    respx.get(f"{BASE}/v1/latest").mock(
        return_value=httpx.Response(200, text="<html>bakim calismasi</html>")
    )

    response = client.get(
        "/tools/convert",
        params={"amount": 100, "from": "EUR", "to": "TRY"},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "upstream_invalid_response"


@respx.mock
def test_same_currency_skips_upstream():
    route = respx.get(f"{BASE}/v1/latest").mock(
        return_value=httpx.Response(200, json={"rates": {"EUR": 1.0}})
    )

    response = client.get(
        "/tools/convert",
        params={"amount": 250, "from": "EUR", "to": "EUR"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rate"] == 1.0
    assert body["result"] == 250.0
    assert route.call_count == 0


@respx.mock
def test_cache_avoids_second_upstream_call():
    route = respx.get(f"{BASE}/v1/2026-08-28").mock(
        return_value=httpx.Response(
            200,
            json={"amount": 1.0, "base": "EUR", "date": "2026-08-28",
                  "rates": {"TRY": 47.1234}},
        )
    )

    params = {"amount": 250, "from": "EUR", "to": "TRY", "date": "2026-08-28"}
    client.get("/tools/convert", params=params)
    client.get("/tools/convert", params=params)

    assert route.call_count == 1