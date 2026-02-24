from fastapi.testclient import TestClient

import api_app


client = TestClient(api_app.app)


def setup_function():
    api_app.DB.clear()


def test_create_and_list_receipts():
    payload = {
        "date": "2026-02-24",
        "store": "Starbucks Gangnam",
        "amount": 9500,
        "category": "식비",
        "items": None,
        "raw_text": "sample",
        "source": "manual"
    }

    resp = client.post("/api/receipts", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["store"] == "Starbucks Gangnam"
    assert data["amount"] == 9500

    list_resp = client.get("/api/receipts")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_stats_endpoint():
    payloads = [
        {
            "date": "2026-02-24",
            "store": "A",
            "amount": 1000,
            "category": "식비",
            "items": None,
            "raw_text": None,
            "source": "manual"
        },
        {
            "date": "2026-02-23",
            "store": "B",
            "amount": 2000,
            "category": "쇼핑",
            "items": None,
            "raw_text": None,
            "source": "manual"
        }
    ]

    for p in payloads:
        resp = client.post("/api/receipts", json=p)
        assert resp.status_code == 200

    stats_resp = client.get("/api/receipts/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_amount"] == 3000
    assert stats["count"] == 2
    assert stats["top_category"] in {"식비", "쇼핑"}
    assert len(stats["daily_series"]) == 2
    assert len(stats["category_series"]) == 2
