from __future__ import annotations

import pandas as pd

from app.services.ensemble import SupplementalForecastResult


class ARIMAForecastService:
    """Generate a local ARIMA forecast when statsmodels is available."""

    def __init__(self, candidate_orders: list[tuple[int, int, int]] | None = None) -> None:
        self.candidate_orders = candidate_orders or [
            (1, 1, 0),
            (2, 1, 0),
            (1, 1, 1),
            (2, 1, 1),
            (3, 1, 1),
        ]

    def forecast(self, series: pd.Series, horizon_days: int) -> SupplementalForecastResult:
        if len(series) < 30:
            return SupplementalForecastResult(
                model_id="arima",
                display_name="ARIMA",
                forecast_values=[],
                status="unavailable",
                detail="ARIMA requires at least 30 observations.",
            )

        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            return SupplementalForecastResult(
                model_id="arima",
                display_name="ARIMA",
                forecast_values=[],
                status="unavailable",
                detail="statsmodels is not installed.",
            )

        clean_series = series.astype(float)
        best_fit = None
        best_order: tuple[int, int, int] | None = None
        best_aic = float("inf")

        for order in self.candidate_orders:
            try:
                model = ARIMA(clean_series, order=order)
                fitted = model.fit()
            except Exception:
                continue

            if fitted.aic < best_aic:
                best_fit = fitted
                best_order = order
                best_aic = float(fitted.aic)

        if best_fit is None or best_order is None:
            return SupplementalForecastResult(
                model_id="arima",
                display_name="ARIMA",
                forecast_values=[],
                status="unavailable",
                detail="ARIMA fitting did not converge for the available data.",
            )

        forecast = best_fit.forecast(steps=horizon_days)
        forecast_values = [round(max(float(value), 0.01), 4) for value in forecast]

        return SupplementalForecastResult(
            model_id="arima",
            display_name="ARIMA",
            forecast_values=forecast_values,
            status="active",
            metadata={"order": str(best_order)},
        )
