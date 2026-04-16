from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FourierForecastResult:
    forecast_values: list[float]
    harmonics_used: int


class FourierForecastService:
    """Create a short-horizon forecast using a filtered Fourier reconstruction."""

    def __init__(self, max_harmonics: int = 5) -> None:
        self.max_harmonics = max_harmonics

    def forecast(self, series: pd.Series, horizon_days: int) -> FourierForecastResult:
        if len(series) < 20:
            raise ValueError("At least 20 observations are required for the Fourier forecast.")

        values = series.astype(float).to_numpy()
        x = np.arange(len(values), dtype=float)

        trend_coefficients = np.polyfit(x, values, deg=1)
        trend = np.polyval(trend_coefficients, x)
        detrended = values - trend

        fft_coefficients = np.fft.rfft(detrended)
        amplitudes = np.abs(fft_coefficients)
        non_zero_indices = np.arange(1, len(amplitudes))

        harmonics_used = min(self.max_harmonics, len(non_zero_indices))
        selected_indices = (
            non_zero_indices[np.argsort(amplitudes[1:])[::-1][:harmonics_used]]
            if harmonics_used > 0
            else np.array([], dtype=int)
        )

        filtered_coefficients = np.zeros_like(fft_coefficients)
        if len(selected_indices) > 0:
            filtered_coefficients[selected_indices] = fft_coefficients[selected_indices]

        periodic_component = np.fft.irfft(filtered_coefficients, n=len(values))
        future_periodic = np.array(
            [periodic_component[(len(values) + offset) % len(values)] for offset in range(horizon_days)],
            dtype=float,
        )

        future_x = np.arange(len(values), len(values) + horizon_days, dtype=float)
        future_trend = np.polyval(trend_coefficients, future_x)
        forecast_values = np.maximum(future_trend + future_periodic, 0.01)

        return FourierForecastResult(
            forecast_values=[round(float(value), 4) for value in forecast_values],
            harmonics_used=harmonics_used,
        )
