import pandas as pd

from app.models.schemas import ForecastRequest
from app.services.ensemble import EnsembleForecastService, SupplementalForecastResult
from app.services.fourier import FourierForecastService
from app.services.market_influence import MarketInfluenceModelService


class FakeHistoricalDataProvider:
    def __init__(self) -> None:
        dates = pd.bdate_range("2025-01-01", periods=80)
        stock_values = [100 + (index * 0.6) + ((index % 5) - 2) for index in range(len(dates))]
        sp500_values = [4000 + (index * 8.0) + ((index % 5) - 2) * 10 for index in range(len(dates))]
        nasdaq_values = [12000 + (index * 2.5) + ((index % 3) - 1) * 6 for index in range(len(dates))]
        dow_values = [34000 + (index * 1.2) + ((index % 4) - 1.5) * 3 for index in range(len(dates))]
        russell_values = [1800 + (index * 0.8) - ((index % 5) - 2) * 4 for index in range(len(dates))]

        self.series_map = {
            "AAPL": pd.Series(stock_values, index=dates, dtype=float),
            "^GSPC": pd.Series(sp500_values, index=dates, dtype=float),
            "^IXIC": pd.Series(nasdaq_values, index=dates, dtype=float),
            "^DJI": pd.Series(dow_values, index=dates, dtype=float),
            "^RUT": pd.Series(russell_values, index=dates, dtype=float),
        }

    def fetch_close_series(
        self,
        ticker: str,
        lookback_days: int,
        end_date: str | None = None,
    ) -> pd.Series:
        series = self.series_map[ticker.strip().upper()]
        if end_date:
            series = series[series.index.date <= pd.Timestamp(end_date).date()]
        return series.tail(lookback_days)


class FakeARIMAService:
    def forecast(self, series: pd.Series, horizon_days: int) -> SupplementalForecastResult:
        last_price = float(series.iloc[-1])
        return SupplementalForecastResult(
            model_id="arima",
            display_name="ARIMA",
            forecast_values=[round(last_price + (index * 0.25), 4) for index in range(1, horizon_days + 1)],
            status="active",
            metadata={"order": "(1, 1, 1)"},
        )


class FakeMLService:
    def forecast(
        self,
        stock_series: pd.Series,
        benchmark_series: pd.Series,
        horizon_days: int,
        projected_benchmark_return: float,
    ) -> SupplementalForecastResult:
        last_price = float(stock_series.iloc[-1])
        return SupplementalForecastResult(
            model_id="xgboost",
            display_name="Local XGBoost",
            forecast_values=[round(last_price + (index * 0.15), 4) for index in range(1, horizon_days + 1)],
            status="active",
            metadata={"training_samples": 48, "feature_count": 10},
        )


def test_fourier_service_returns_full_overlay_curves() -> None:
    dates = pd.bdate_range("2025-01-01", periods=40)
    values = [1.25 + (index * 0.02) + ((index % 4) - 1.5) * 0.08 for index in range(len(dates))]
    series = pd.Series(values, index=dates, dtype=float)

    result = FourierForecastService(max_harmonics=3).forecast(series=series, horizon_days=6)

    expected_overlay_length = len(series) + 6
    assert len(result.forecast_values) == 6
    assert len(result.trend_line) == expected_overlay_length
    assert len(result.fourier_model) == expected_overlay_length
    assert len(result.error_upper_bound) == expected_overlay_length
    assert len(result.error_lower_bound) == expected_overlay_length
    assert min(result.error_lower_bound) >= 0.01
    assert result.error_margin >= 0.0
    assert "1.96 * RMSE" in result.error_method


def test_market_influence_model_returns_intermediate_outputs() -> None:
    service = MarketInfluenceModelService(
        data_provider=FakeHistoricalDataProvider(),
        fourier_service=FourierForecastService(max_harmonics=3),
        arima_service=FakeARIMAService(),
        ml_service=FakeMLService(),
        ensemble_service=EnsembleForecastService(),
    )

    response = service.run(
        ForecastRequest(
            ticker="AAPL",
            horizon_days=10,
            analysis_window_days=60,
        )
    )

    assert response.ticker == "AAPL"
    assert len(response.historical_prices) == 60
    assert len(response.benchmark_candidates) == 4
    assert response.summary.selected_benchmark is not None
    assert len(response.stock_fourier_forecast) == 10
    assert len(response.benchmark_projected_forecast) == 10
    assert len(response.index_based_forecast) == 10
    assert len(response.final_combined_forecast) == 10
    assert len(response.arima_forecast) == 10
    assert len(response.ml_forecast) == 10
    assert len(response.ensemble_forecast) == 10
    assert len(response.ensemble_components) == 3
    assert len(response.fourier_overlay.trend_line) == 70
    assert len(response.fourier_overlay.fourier_model) == 70
    assert len(response.fourier_overlay.error_upper_bound) == 70
    assert len(response.fourier_overlay.error_lower_bound) == 70
    assert min(point.value for point in response.fourier_overlay.error_lower_bound) >= 0.01
    assert response.fourier_overlay.error_method is not None
    assert response.diagnostics.fourier_harmonics_used == 3
    assert response.diagnostics.arima_order == "(1, 1, 1)"
    assert response.diagnostics.ml_training_samples == 48
    assert response.diagnostics.ensemble_method is not None
    assert 0.0 <= response.summary.alpha <= 1.0
    assert 0.0 <= response.summary.confidence_score <= 1.0
    assert response.diagnostics.benchmark_agreement_score is not None
    assert response.diagnostics.recent_volatility is not None
    assert response.summary.current_price == round(response.historical_prices[-1].value, 4)
    assert response.summary.current_price_date == response.historical_prices[-1].date
    assert response.summary.predicted_price is not None
    assert response.summary.predicted_price_change is not None
    assert response.summary.predicted_price_change == round(
        response.summary.predicted_price - response.summary.current_price,
        4,
    )


def test_market_influence_model_uses_requested_analysis_end_date() -> None:
    service = MarketInfluenceModelService(
        data_provider=FakeHistoricalDataProvider(),
        fourier_service=FourierForecastService(max_harmonics=3),
        arima_service=FakeARIMAService(),
        ml_service=FakeMLService(),
        ensemble_service=EnsembleForecastService(),
    )

    response = service.run(
        ForecastRequest(
            ticker="AAPL",
            horizon_days=5,
            analysis_window_days=60,
            analysis_end_date="2025-03-31",
        )
    )

    assert response.analysis_window.end_date == "2025-03-31"
    assert response.summary.current_price_date == "2025-03-31"
    assert response.stock_fourier_forecast[0].date == "2025-04-01"


def test_market_influence_model_applies_fallback_for_unrealistic_forecast() -> None:
    class ExtremeFourierService:
        def forecast(self, series: pd.Series, horizon_days: int):
            class Result:
                forecast_values = [float(series.iloc[-1] * 2.0) for _ in range(horizon_days)]
                harmonics_used = 1

            return Result()

    service = MarketInfluenceModelService(
        data_provider=FakeHistoricalDataProvider(),
        fourier_service=ExtremeFourierService(),
        arima_service=FakeARIMAService(),
        ml_service=FakeMLService(),
        ensemble_service=EnsembleForecastService(),
    )

    response = service.run(
        ForecastRequest(
            ticker="AAPL",
            horizon_days=10,
            analysis_window_days=60,
        )
    )

    assert response.diagnostics.fallback_applied is True
    assert response.summary.warning_status == "high"
    assert response.warning_banner is not None
    assert "Fallback logic" in response.warning_banner.message
