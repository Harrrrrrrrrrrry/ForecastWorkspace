import pytest
from app.api.routes.explanations import forecast_explanation_service, explanation_rate_limiter
from app.core.config import get_settings
from app.main import app
from app.models.schemas import ExplanationResponse, ForecastResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_explanation_rate_limiter():
    explanation_rate_limiter.reset()
    yield
    explanation_rate_limiter.reset()


def test_explanations_endpoint_returns_grounded_sections_without_authentication(monkeypatch) -> None:
    def fake_explain(forecast):
        return {
            "model": "gpt-5.4-mini",
            "ai_confidence_percent": 67,
            "ai_verdict": "I would treat this forecast number as moderately believable.",
            "reasoning_summary": "Benchmark alignment is reasonable, but the safeguards still make this educational rather than financial advice.",
            "forecast_signal": "bullish",
        }

    monkeypatch.setattr(forecast_explanation_service, "explain", fake_explain)

    response = client.post(
        "/api/v1/explanations",
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
    assert payload["ai_confidence_percent"] == 67
    assert "moderately believable" in payload["ai_verdict"]
    assert payload["forecast_signal"] == "bullish"


def test_explanations_endpoint_enforces_ip_hourly_limit(monkeypatch) -> None:
    monkeypatch.setattr(explanation_rate_limiter.settings, "explanation_ip_hourly_limit", 1)
    monkeypatch.setattr(explanation_rate_limiter.settings, "explanation_global_daily_limit", 50)
    monkeypatch.setattr(
        forecast_explanation_service,
        "explain",
        lambda forecast: {
            "model": "gpt-5.4-mini",
            "ai_confidence_percent": 55,
            "ai_verdict": "I would not fully trust this exact price target.",
            "reasoning_summary": "The model has limits and this is not financial advice.",
            "forecast_signal": "neutral",
        },
    )

    response = client.post(
        "/api/v1/explanations",
        headers={"x-forwarded-for": "203.0.113.10"},
        json=minimal_explanation_payload(),
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/explanations",
        headers={"x-forwarded-for": "203.0.113.10"},
        json=minimal_explanation_payload(),
    )

    assert response.status_code == 429
    assert response.json() == {
        "detail": "GPT explanation limit reached for this IP address. Please try again later."
    }


def test_explanations_endpoint_enforces_global_daily_limit(monkeypatch) -> None:
    monkeypatch.setattr(explanation_rate_limiter.settings, "explanation_ip_hourly_limit", 50)
    monkeypatch.setattr(explanation_rate_limiter.settings, "explanation_global_daily_limit", 1)
    monkeypatch.setattr(
        forecast_explanation_service,
        "explain",
        lambda forecast: {
            "model": "gpt-5.4-mini",
            "ai_confidence_percent": 55,
            "ai_verdict": "I would not fully trust this exact price target.",
            "reasoning_summary": "The model has limits and this is not financial advice.",
            "forecast_signal": "neutral",
        },
    )

    response = client.post(
        "/api/v1/explanations",
        headers={"x-forwarded-for": "203.0.113.10"},
        json=minimal_explanation_payload(),
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/explanations",
        headers={"x-forwarded-for": "203.0.113.11"},
        json=minimal_explanation_payload(),
    )

    assert response.status_code == 429
    assert response.json() == {
        "detail": "The daily GPT explanation limit for this site has been reached. Please try again tomorrow."
    }


def test_explanations_endpoint_rejects_oversized_request_body(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "explanation_max_request_body_bytes", 32)

    response = client.post(
        "/api/v1/explanations",
        json=minimal_explanation_payload(),
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Explanation request body is too large."}


def test_explanations_endpoint_reports_missing_api_key(monkeypatch) -> None:
    def fake_explain(forecast):
        raise RuntimeError("OpenAI API key is not configured.")

    monkeypatch.setattr(forecast_explanation_service, "explain", fake_explain)

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

    assert response.status_code == 503
    assert response.json() == {"detail": "OpenAI API key is not configured."}


def test_explanation_response_rejects_invalid_forecast_signal() -> None:
    with pytest.raises(ValidationError):
        ExplanationResponse(
            model="gpt-5.4-mini",
            ai_confidence_percent=50,
            ai_verdict="I would not fully trust this exact price target.",
            reasoning_summary="Signals are heuristic and this is not financial advice.",
            forecast_signal="buy",
        )


def test_explanation_response_rejects_invalid_ai_confidence_percent() -> None:
    with pytest.raises(ValidationError):
        ExplanationResponse(
            model="gpt-5.4-mini",
            ai_confidence_percent=101,
            ai_verdict="I would trust this forecast number.",
            reasoning_summary="Signals are strong, but this is not financial advice.",
            forecast_signal="bullish",
        )


def test_parse_json_response_requires_exact_keys_valid_signal_and_confidence_percent() -> None:
    service = forecast_explanation_service

    with pytest.raises(ValueError, match="unexpected keys: extra_field"):
        service._parse_json_response(
            """
            {
              "ai_confidence_percent": 67,
              "ai_verdict": "I would trust this forecast number.",
              "reasoning_summary": "Signals are strong, but this is not financial advice.",
              "forecast_signal": "bullish",
              "extra_field": "should fail"
            }
            """
        )

    with pytest.raises(ValueError, match="invalid forecast_signal"):
        service._parse_json_response(
            """
            {
              "ai_confidence_percent": 67,
              "ai_verdict": "I would trust this forecast number.",
              "reasoning_summary": "Signals are strong, but this is not financial advice.",
              "forecast_signal": "hold"
            }
            """
        )

    with pytest.raises(ValueError, match="between 0 and 100"):
        service._parse_json_response(
            """
            {
              "ai_confidence_percent": 101,
              "ai_verdict": "I would trust this forecast number.",
              "reasoning_summary": "Signals are strong, but this is not financial advice.",
              "forecast_signal": "bullish"
            }
            """
        )


def test_prompts_require_direct_forecast_number_trust_assessment() -> None:
    service = forecast_explanation_service
    system_prompt = service._system_prompt()
    user_prompt = service._user_prompt(ExplanationResponseTestPayload.forecast())
    combined_prompt = f"{system_prompt} {user_prompt}"

    assert "whether the forecast number itself looks believable" in system_prompt
    assert "ai_confidence_percent must be an integer from 0 to 100" in system_prompt
    assert "AI-derived confidence" in user_prompt
    assert "Each text section must be at most two clear, direct sentences" in user_prompt
    assert "summary.predicted_price" in user_prompt
    assert "summary.predicted_percent_change" in user_prompt
    assert "I would not fully trust this exact price target" in user_prompt
    assert "I would be skeptical of this number" in user_prompt
    assert "diagnostics.fallback_applied" in user_prompt
    assert "diagnostics.benchmark_agreement_score" in user_prompt
    assert "diagnostics.recent_volatility" in user_prompt
    assert "ensemble_components" in user_prompt
    assert "Do not output buy, sell, or hold advice" in combined_prompt
    assert "Do not generate a new prediction" in combined_prompt


class ExplanationResponseTestPayload:
    @staticmethod
    def forecast() -> ForecastResponse:
        return ForecastResponse(**minimal_explanation_payload()["forecast"])


def minimal_explanation_payload() -> dict:
    return {
        "forecast": {
            "ticker": "AAPL",
            "horizon_days": 14,
            "analysis_window": {
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
                "lookback_days": 60,
            },
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
