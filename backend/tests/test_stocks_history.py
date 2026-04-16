from fastapi.testclient import TestClient

from app.main import app
from app.services.stocks import StockHistoryService


client = TestClient(app)


def test_stock_history_endpoint_returns_structured_points(monkeypatch) -> None:
    def fake_get_history(self: StockHistoryService, ticker: str, lookback_days: int = 180):
        return {
            "ticker": ticker.upper(),
            "source": "yfinance",
            "lookback_days": lookback_days,
            "points": [
                {"date": "2026-03-30", "close": 221.13},
                {"date": "2026-03-31", "close": 223.45},
            ],
        }

    monkeypatch.setattr(StockHistoryService, "get_history", fake_get_history)

    response = client.get("/api/v1/stocks/aapl/history?lookback_days=120")

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "source": "yfinance",
        "lookback_days": 120,
        "points": [
            {"date": "2026-03-30", "close": 221.13},
            {"date": "2026-03-31", "close": 223.45},
        ],
    }


def test_stock_history_endpoint_maps_lookup_errors(monkeypatch) -> None:
    def fake_get_history(self: StockHistoryService, ticker: str, lookback_days: int = 180):
        raise LookupError("No historical price data found for ticker 'BAD'.")

    monkeypatch.setattr(StockHistoryService, "get_history", fake_get_history)

    response = client.get("/api/v1/stocks/BAD/history")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No historical price data found for ticker 'BAD'."
    }
