import pytest
from app.main import app
from app.api.routes.explanations import forecast_explanation_service
from app.models.schemas import ExplanationResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError


client = TestClient(app)


def test_explanations_endpoint_requires_authentication() -> None:
    response = client.post(
        "/api/v1/explanations",
        json={
            "forecast": {
                "ticker": "AAPL",
                "horizon_days": 14,
                "analysis_window": {"start_date": "2026-01-01", "end_date": "2026-03-31", "lookback_days": 60},
                "historical_prices": [],
                "benchmark_candidates": [],
                "selected_benchmark_history": [],
                "stock_fourier_forecast": [],
                "benchmark_projected_forecast": [],
                "index_based_forecast": [],
                "final_combined_forecast": [],
                "diagnostics": {
                    "analysis_method": "Pearson correlation on aligned daily returns.",
                    "outlier_detected": False,
                    "fallback_applied": False,
                },
                "summary": {},
                "warning_banner": None,
                "warnings": [],
                "limitations": [],
            }
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}


def test_explanations_endpoint_returns_grounded_sections(monkeypatch, approved_auth_headers) -> None:
    def fake_explain(forecast):
        return {
            "model": "gpt-5.4-mini",
            "plain_language_explanation": "The model projects a modest increase over the forecast horizon.",
            "reliability_summary": "Confidence is moderate because benchmark alignment is reasonable.",
            "limitations_summary": "The forecast depends on historical patterns and heuristic safeguards.",
            "forecast_signal": "bullish",
            "disclaimer": "This tool is educational and not financial advice.",
        }

    monkeypatch.setattr(forecast_explanation_service, "explain", fake_explain)

    response = client.post(
        "/api/v1/explanations",
        headers=approved_auth_headers,
        json={
            "forecast": {
                "ticker": "AAPL",
                "horizon_days": 14,
                "analysis_window": {
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
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
                    "benchmark_agreement_score": 0.75,
                    "recent_volatility": 0.018,
                    "forecast_outlier_score": 1.2,
                    "outlier_detected": False,
                    "fallback_applied": False,
                    "fallback_reason": None,
                },
                "summary": {
                    "selected_benchmark": "S&P 500 (^GSPC)",
                    "alpha": 0.82,
                    "current_price": 210.0,
                    "current_price_date": "2026-03-31",
                    "predicted_price": 210.9,
                    "predicted_price_change": 0.9,
                    "predicted_percent_change": 0.43,
                    "confidence_score": 0.67,
                    "warning_status": "low",
                },
                "warning_banner": {
                    "level": "low",
                    "title": "Moderate Confidence",
                    "message": "The model found a usable signal, but benchmark agreement or volatility reduced confidence.",
                },
                "warnings": [],
                "limitations": [
                    "Phase 5 reliability rules are heuristic safeguards rather than guarantees of forecast accuracy."
                ],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "gpt-5.4-mini"
    assert "modest increase" in payload["plain_language_explanation"]
    assert payload["forecast_signal"] == "bullish"


def test_explanations_endpoint_reports_missing_api_key(monkeypatch) -> None:
    def fake_explain(forecast):
        raise RuntimeError("OpenAI API key is not configured.")

    monkeypatch.setattr(forecast_explanation_service, "explain", fake_explain)

    client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "approved@example.com",
            "password": "strongpass1",
        },
    )
    sign_in_response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "approved@example.com",
            "password": "strongpass1",
        },
    )
    token = sign_in_response.json()["token"]

    response = client.post(
        "/api/v1/explanations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "forecast": {
                "ticker": "AAPL",
                "horizon_days": 14,
                "analysis_window": {"start_date": "2026-01-01", "end_date": "2026-03-31", "lookback_days": 60},
                "historical_prices": [],
                "benchmark_candidates": [],
                "selected_benchmark_history": [],
                "stock_fourier_forecast": [],
                "benchmark_projected_forecast": [],
                "index_based_forecast": [],
                "final_combined_forecast": [],
                "diagnostics": {
                    "analysis_method": "Pearson correlation on aligned daily returns.",
                    "outlier_detected": False,
                    "fallback_applied": False,
                },
                "summary": {},
                "warning_banner": None,
                "warnings": [],
                "limitations": [],
            }
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "OpenAI API key is not configured."}


def test_explanations_endpoint_enforces_daily_query_limit(
    monkeypatch,
    approved_auth_headers,
) -> None:
    monkeypatch.setattr(
        forecast_explanation_service,
        "explain",
        lambda forecast: {
            "model": "gpt-5.4-mini",
            "plain_language_explanation": "Explanation.",
            "reliability_summary": "Reliable enough.",
            "limitations_summary": "Has limits.",
            "forecast_signal": "neutral",
            "disclaimer": "Not financial advice.",
        },
    )
    from app.services.auth import auth_service

    monkeypatch.setattr(auth_service.settings, "daily_query_limit", 2)

    payload = {
        "forecast": {
            "ticker": "AAPL",
            "horizon_days": 14,
            "analysis_window": {"start_date": "2026-01-01", "end_date": "2026-03-31", "lookback_days": 60},
            "historical_prices": [],
            "benchmark_candidates": [],
            "selected_benchmark_history": [],
            "stock_fourier_forecast": [],
            "benchmark_projected_forecast": [],
            "index_based_forecast": [],
            "final_combined_forecast": [],
            "diagnostics": {
                "analysis_method": "Pearson correlation on aligned daily returns.",
                "outlier_detected": False,
                "fallback_applied": False,
            },
            "summary": {},
            "warning_banner": None,
            "warnings": [],
            "limitations": [],
        }
    }

    for _ in range(2):
        response = client.post("/api/v1/explanations", headers=approved_auth_headers, json=payload)
        assert response.status_code == 200

    response = client.post("/api/v1/explanations", headers=approved_auth_headers, json=payload)

    assert response.status_code == 429
    assert response.json() == {"detail": "Today's GPT explanation quota is exhausted. Please try again tomorrow."}


def test_explanation_response_rejects_invalid_forecast_signal() -> None:
    with pytest.raises(ValidationError):
        ExplanationResponse(
            model="gpt-5.4-mini",
            plain_language_explanation="Slight upward move.",
            reliability_summary="Confidence is moderate.",
            limitations_summary="Signals are heuristic.",
            forecast_signal="buy",
            disclaimer="Not financial advice.",
        )


def test_parse_json_response_requires_exact_keys_and_valid_signal() -> None:
    service = forecast_explanation_service

    with pytest.raises(ValueError, match="unexpected keys: extra_field"):
        service._parse_json_response(
            """
            {
              "plain_language_explanation": "Modest increase.",
              "reliability_summary": "Moderate confidence.",
              "limitations_summary": "Heuristic limitations apply.",
              "forecast_signal": "bullish",
              "disclaimer": "Not financial advice.",
              "extra_field": "should fail"
            }
            """
        )

    with pytest.raises(ValueError, match="invalid forecast_signal"):
        service._parse_json_response(
            """
            {
              "plain_language_explanation": "Modest increase.",
              "reliability_summary": "Moderate confidence.",
              "limitations_summary": "Heuristic limitations apply.",
              "forecast_signal": "hold",
              "disclaimer": "Not financial advice."
            }
            """
        )
