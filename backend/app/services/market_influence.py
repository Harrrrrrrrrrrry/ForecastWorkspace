from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from app.models.schemas import (
    AnalysisWindow,
    BenchmarkCandidate,
    EnsembleComponent,
    ForecastRequest,
    ForecastResponse,
    ForecastSummary,
    ModelDiagnostics,
    PricePoint,
    WarningBanner,
)
from app.services.arima import ARIMAForecastService
from app.services.benchmarks import BENCHMARK_INDICES, BenchmarkIndex
from app.services.data_provider import HistoricalDataProvider
from app.services.ensemble import EnsembleForecastService, SupplementalForecastResult
from app.services.fourier import FourierForecastService
from app.services.ml_forecast import XGBoostForecastService
from app.services.reliability import ReliabilityService


class MarketInfluenceModelService:
    """Run the Market Influence Model using benchmark correlation and forecast blending."""

    def __init__(
        self,
        data_provider: HistoricalDataProvider | None = None,
        fourier_service: FourierForecastService | None = None,
        reliability_service: ReliabilityService | None = None,
        arima_service: ARIMAForecastService | None = None,
        ml_service: XGBoostForecastService | None = None,
        ensemble_service: EnsembleForecastService | None = None,
    ) -> None:
        self.data_provider = data_provider or HistoricalDataProvider()
        self.fourier_service = fourier_service or FourierForecastService()
        self.reliability_service = reliability_service or ReliabilityService()
        self.arima_service = arima_service or ARIMAForecastService()
        self.ml_service = ml_service or XGBoostForecastService()
        self.ensemble_service = ensemble_service or EnsembleForecastService()

    def run(self, payload: ForecastRequest) -> ForecastResponse:
        normalized_ticker = payload.ticker.strip().upper()
        stock_series = self.data_provider.fetch_close_series(
            ticker=normalized_ticker,
            lookback_days=payload.analysis_window_days,
        )

        benchmark_correlations: list[BenchmarkCandidate] = []
        benchmark_histories: dict[str, pd.Series] = {}
        benchmark_betas: dict[str, float] = {}
        warnings: list[str] = []

        for benchmark in BENCHMARK_INDICES:
            try:
                benchmark_series = self.data_provider.fetch_close_series(
                    ticker=benchmark.symbol,
                    lookback_days=payload.analysis_window_days,
                )
                aligned_stock_returns, aligned_benchmark_returns = self._align_returns(
                    stock_series=stock_series,
                    benchmark_series=benchmark_series,
                )

                correlation = float(aligned_stock_returns.corr(aligned_benchmark_returns))
                if np.isnan(correlation):
                    continue

                beta = self._calculate_beta(
                    stock_returns=aligned_stock_returns,
                    benchmark_returns=aligned_benchmark_returns,
                )

                benchmark_correlations.append(
                    BenchmarkCandidate(
                        symbol=benchmark.symbol,
                        name=benchmark.name,
                        correlation=round(correlation, 4),
                    )
                )
                benchmark_histories[benchmark.symbol] = benchmark_series
                benchmark_betas[benchmark.symbol] = beta
            except (LookupError, ValueError):
                warnings.append(f"Benchmark data unavailable for {benchmark.name} ({benchmark.symbol}).")

        if not benchmark_correlations:
            raise LookupError("Unable to evaluate benchmark indices for the requested stock.")

        sorted_candidates = sorted(
            benchmark_correlations,
            key=lambda candidate: candidate.correlation,
            reverse=True,
        )
        selected_candidate = sorted_candidates[0]
        selected_benchmark = self._lookup_benchmark(selected_candidate.symbol)
        selected_benchmark_series = benchmark_histories[selected_candidate.symbol]

        stock_fourier_result = self.fourier_service.forecast(
            series=stock_series,
            horizon_days=payload.horizon_days,
        )
        future_dates = self._generate_future_dates(stock_series.index[-1], payload.horizon_days)

        benchmark_projected_return = self._project_benchmark_daily_return(selected_benchmark_series)
        benchmark_projected_prices = self._project_benchmark_prices(
            benchmark_series=selected_benchmark_series,
            projected_daily_return=benchmark_projected_return,
            horizon_days=payload.horizon_days,
        )

        index_based_prices = self._project_index_based_stock_forecast(
            stock_series=stock_series,
            beta=benchmark_betas[selected_candidate.symbol],
            benchmark_projected_return=benchmark_projected_return,
            horizon_days=payload.horizon_days,
        )

        alpha = self._clamp_alpha(selected_candidate.correlation)
        raw_combined_prices = [
            round(alpha * fourier_price + (1.0 - alpha) * index_price, 4)
            for fourier_price, index_price in zip(
                stock_fourier_result.forecast_values,
                index_based_prices,
                strict=True,
            )
        ]

        reliability = self.reliability_service.assess(
            stock_series=stock_series,
            stock_fourier_prices=stock_fourier_result.forecast_values,
            index_based_prices=index_based_prices,
            combined_prices=raw_combined_prices,
            correlation=selected_candidate.correlation,
            alpha=alpha,
        )

        historical_points = self._series_to_price_points(stock_series)
        selected_benchmark_points = self._series_to_price_points(selected_benchmark_series)
        stock_fourier_forecast = self._forecast_to_points(future_dates, stock_fourier_result.forecast_values)
        benchmark_projected_forecast = self._forecast_to_points(future_dates, benchmark_projected_prices)
        index_based_forecast = self._forecast_to_points(future_dates, index_based_prices)
        final_combined_forecast = self._forecast_to_points(future_dates, reliability.final_prices)

        arima_result = self.arima_service.forecast(
            series=stock_series,
            horizon_days=payload.horizon_days,
        )
        ml_result = self.ml_service.forecast(
            stock_series=stock_series,
            benchmark_series=selected_benchmark_series,
            horizon_days=payload.horizon_days,
            projected_benchmark_return=benchmark_projected_return,
        )
        ensemble_result = self.ensemble_service.build(
            core_prices=reliability.final_prices,
            arima_result=arima_result,
            ml_result=ml_result,
            core_confidence=reliability.confidence_score,
        )

        supplemental_warnings = self._build_supplemental_model_warnings(
            arima_result=arima_result,
            ml_result=ml_result,
        )
        arima_forecast = (
            self._forecast_to_points(future_dates, arima_result.forecast_values)
            if arima_result.forecast_values
            else []
        )
        ml_forecast = (
            self._forecast_to_points(future_dates, ml_result.forecast_values)
            if ml_result.forecast_values
            else []
        )
        ensemble_forecast = self._forecast_to_points(future_dates, ensemble_result.forecast_values)
        ensemble_components = [
            EnsembleComponent(
                model_id=component.model_id,
                display_name=component.display_name,
                weight=component.weight,
                terminal_price=component.terminal_price,
                status=component.status,
                detail=component.detail,
            )
            for component in ensemble_result.components
        ]

        last_close = float(stock_series.iloc[-1])
        last_close_date = stock_series.index[-1].strftime("%Y-%m-%d")
        predicted_price = ensemble_result.forecast_values[-1]
        predicted_price_change = predicted_price - last_close
        predicted_percent_change = ((predicted_price - last_close) / last_close) * 100

        return ForecastResponse(
            ticker=normalized_ticker,
            horizon_days=payload.horizon_days,
            analysis_window=AnalysisWindow(
                start_date=stock_series.index[0].strftime("%Y-%m-%d"),
                end_date=stock_series.index[-1].strftime("%Y-%m-%d"),
                lookback_days=len(stock_series),
            ),
            historical_prices=historical_points,
            benchmark_candidates=sorted_candidates,
            selected_benchmark_history=selected_benchmark_points,
            stock_fourier_forecast=stock_fourier_forecast,
            benchmark_projected_forecast=benchmark_projected_forecast,
            index_based_forecast=index_based_forecast,
            final_combined_forecast=final_combined_forecast,
            arima_forecast=arima_forecast,
            ml_forecast=ml_forecast,
            ensemble_forecast=ensemble_forecast,
            ensemble_components=ensemble_components,
            diagnostics=ModelDiagnostics(
                analysis_method="Pearson correlation on aligned daily returns.",
                selected_benchmark_symbol=selected_candidate.symbol,
                selected_benchmark_name=selected_benchmark.name,
                selected_correlation=selected_candidate.correlation,
                stock_beta_to_benchmark=round(benchmark_betas[selected_candidate.symbol], 4),
                projected_benchmark_daily_return=round(benchmark_projected_return, 6),
                fourier_harmonics_used=stock_fourier_result.harmonics_used,
                benchmark_agreement_score=reliability.benchmark_agreement_score,
                recent_volatility=reliability.recent_volatility,
                forecast_outlier_score=reliability.outlier_score,
                outlier_detected=reliability.outlier_detected,
                fallback_applied=reliability.fallback_applied,
                fallback_reason=reliability.fallback_reason,
                arima_order=str(arima_result.metadata.get("order")) if arima_result.metadata else None,
                arima_status=arima_result.status,
                ml_model_name=ml_result.display_name,
                ml_status=ml_result.status,
                ml_training_samples=(
                    int(ml_result.metadata["training_samples"])
                    if "training_samples" in ml_result.metadata
                    else None
                ),
                ensemble_method=ensemble_result.method,
            ),
            summary=ForecastSummary(
                selected_benchmark=f"{selected_benchmark.name} ({selected_candidate.symbol})",
                alpha=round(alpha, 4),
                current_price=round(last_close, 4),
                current_price_date=last_close_date,
                predicted_price=round(predicted_price, 4),
                predicted_price_change=round(predicted_price_change, 4),
                predicted_percent_change=round(predicted_percent_change, 4),
                confidence_score=reliability.confidence_score,
                warning_status=reliability.warning_status,
            ),
            warning_banner=(
                WarningBanner(
                    level=reliability.warning_banner_level,
                    title=reliability.warning_banner_title,
                    message=reliability.warning_banner_message,
                )
                if reliability.warning_banner_level
                and reliability.warning_banner_title
                and reliability.warning_banner_message
                    else None
            ),
            warnings=warnings + reliability.warnings + supplemental_warnings,
            limitations=[
                "Phase 3 uses a simple benchmark projection based on recent average index returns.",
                "The Fourier forecast extrapolates recurring historical price patterns and does not model exogenous events.",
                "Phase 5 reliability rules are heuristic safeguards rather than guarantees of forecast accuracy.",
                "ARIMA and local XGBoost are supplemental models whose value depends on dependency availability and local training stability.",
            ],
        )

    def _align_returns(
        self,
        stock_series: pd.Series,
        benchmark_series: pd.Series,
    ) -> tuple[pd.Series, pd.Series]:
        aligned = pd.concat(
            [stock_series.pct_change(), benchmark_series.pct_change()],
            axis=1,
            join="inner",
        ).dropna()

        if len(aligned) < 20:
            raise ValueError("Insufficient overlapping history for correlation analysis.")

        return aligned.iloc[:, 0], aligned.iloc[:, 1]

    def _calculate_beta(self, stock_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        benchmark_variance = float(np.var(benchmark_returns))
        if benchmark_variance == 0:
            return 0.0

        covariance = float(np.cov(stock_returns, benchmark_returns)[0, 1])
        return covariance / benchmark_variance

    def _project_benchmark_daily_return(self, benchmark_series: pd.Series) -> float:
        benchmark_returns = benchmark_series.pct_change().dropna()
        projection_window = min(10, len(benchmark_returns))
        if projection_window == 0:
            return 0.0

        return float(benchmark_returns.tail(projection_window).mean())

    def _project_benchmark_prices(
        self,
        benchmark_series: pd.Series,
        projected_daily_return: float,
        horizon_days: int,
    ) -> list[float]:
        prices: list[float] = []
        current_price = float(benchmark_series.iloc[-1])
        for _ in range(horizon_days):
            current_price *= 1.0 + projected_daily_return
            prices.append(round(current_price, 4))
        return prices

    def _project_index_based_stock_forecast(
        self,
        stock_series: pd.Series,
        beta: float,
        benchmark_projected_return: float,
        horizon_days: int,
    ) -> list[float]:
        prices: list[float] = []
        current_price = float(stock_series.iloc[-1])
        implied_stock_return = beta * benchmark_projected_return

        for _ in range(horizon_days):
            current_price *= 1.0 + implied_stock_return
            prices.append(round(max(current_price, 0.01), 4))

        return prices

    def _series_to_price_points(self, series: pd.Series) -> list[PricePoint]:
        return [
            PricePoint(date=index.strftime("%Y-%m-%d"), value=round(float(value), 4))
            for index, value in series.items()
        ]

    def _forecast_to_points(
        self,
        dates: list[pd.Timestamp],
        values: list[float],
    ) -> list[PricePoint]:
        return [
            PricePoint(date=date.strftime("%Y-%m-%d"), value=round(float(value), 4))
            for date, value in zip(dates, values, strict=True)
        ]

    def _generate_future_dates(self, last_date: pd.Timestamp, horizon_days: int) -> list[pd.Timestamp]:
        future_index = pd.date_range(last_date + BDay(1), periods=horizon_days, freq=BDay())
        return [pd.Timestamp(date) for date in future_index]

    def _lookup_benchmark(self, symbol: str) -> BenchmarkIndex:
        for benchmark in BENCHMARK_INDICES:
            if benchmark.symbol == symbol:
                return benchmark
        raise LookupError(f"Unknown benchmark symbol '{symbol}'.")

    def _clamp_alpha(self, correlation: float) -> float:
        return max(0.0, min(1.0, float(correlation)))

    def _build_supplemental_model_warnings(
        self,
        arima_result: SupplementalForecastResult,
        ml_result: SupplementalForecastResult,
    ) -> list[str]:
        warnings: list[str] = []
        if arima_result.status != "active" and arima_result.detail:
            warnings.append(f"ARIMA forecast unavailable: {arima_result.detail}")
        if ml_result.status != "active" and ml_result.detail:
            warnings.append(f"Local XGBoost forecast unavailable: {ml_result.detail}")
        return warnings
