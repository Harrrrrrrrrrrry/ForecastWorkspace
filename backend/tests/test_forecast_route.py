from app.api.routes.forecast import market_influence_service
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_forecast_endpoint_returns_structured_response_without_authentication(monkeypatch) -> None:
    def fake_run(payload):
        return {
            "ticker": payload.ticker.upper(),
            "horizon_days": payload.horizon_days,
            "analysis_window": {
                "start_date": "2026-01-01",
                "end_date": payload.analysis_end_date or "2026-03-31",
                "lookback_days": 60,
            },
            "historical_prices": [{"date": "2026-03-31", "value": 210.0}],
            "benchmark_candidates": [
                {"symbol": "^GSPC", "name": "S&P 500", "correlation": 0.82}
            ],
            "selected_benchmark_history": [{"date": "2026-03-31", "value": 5600.0}],
            "stock_fourier_forecast": [{"date": "2026-04-01", "value": 211.0}],
            "benchmark_projected_forecast": [{"date": "2026-04-01", "value": 5612.0}],
            "index_based_forecast": [{"date": "2026-04-01", "value": 210.6}],
            "final_combined_forecast": [{"date": "2026-04-01", "value": 210.9}],
            "diagnostics": {
                "analysis_method": "Pearson correlation on aligned daily returns.",
                "selected_benchmark_symbol": "^GSPC",
                "selected_benchmark_name": "S&P 500",
                "selected_correlation": 0.82,
                "stock_beta_to_benchmark": 1.1,
                "projected_benchmark_daily_return": 0.002,
                "fourier_harmonics_used": 3,
            },
            "summary": {
                "selected_benchmark": "S&P 500 (^GSPC)",
                "alpha": 0.82,
                "current_price": 210.0,
                "current_price_date": "2026-03-31",
                "predicted_price": 210.9,
                "predicted_price_change": 0.9,
                "predicted_percent_change": 0.43,
                "confidence_score": 0.82,
                "warning_status": "normal",
            },
            "warnings": [],
            "limitations": ["Example limitation"],
        }

    monkeypatch.setattr(market_influence_service, "run", fake_run)

    response = client.post(
        "/api/v1/forecast",
        json={
            "ticker": "aapl",
            "horizon_days": 7,
            "analysis_window_days": 60,
            "analysis_end_date": "2026-03-31",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert payload["benchmark_candidates"][0]["symbol"] == "^GSPC"
    assert payload["final_combined_forecast"][0]["value"] == 210.9
    assert payload["summary"]["current_price"] == 210.0
    assert payload["analysis_window"]["end_date"] == "2026-03-31"
    assert payload["summary"]["current_price_date"] == "2026-03-31"
    assert payload["summary"]["predicted_price_change"] == 0.9
