from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ReliabilityAssessment:
    confidence_score: float
    warning_status: str
    warning_banner_level: str | None
    warning_banner_title: str | None
    warning_banner_message: str | None
    warnings: list[str]
    outlier_detected: bool
    outlier_score: float
    benchmark_agreement_score: float
    recent_volatility: float
    fallback_applied: bool
    fallback_reason: str | None
    final_prices: list[float]


class ReliabilityService:
    """Evaluate whether the raw forecast is trustworthy enough to present directly."""

    def assess(
        self,
        stock_series: pd.Series,
        stock_fourier_prices: list[float],
        index_based_prices: list[float],
        combined_prices: list[float],
        correlation: float,
        alpha: float,
    ) -> ReliabilityAssessment:
        last_close = float(stock_series.iloc[-1])
        recent_returns = stock_series.pct_change().dropna()
        recent_volatility = float(recent_returns.tail(min(20, len(recent_returns))).std(ddof=0) or 0.0)

        benchmark_agreement_score = self._calculate_agreement_score(
            stock_fourier_prices=stock_fourier_prices,
            index_based_prices=index_based_prices,
            last_close=last_close,
        )
        outlier_score, outlier_detected = self._detect_outlier(
            stock_series=stock_series,
            combined_prices=combined_prices,
            last_close=last_close,
        )

        fallback_applied = False
        fallback_reason: str | None = None
        final_prices = list(combined_prices)
        warnings: list[str] = []

        if outlier_detected:
            warnings.append(
                "The raw combined forecast was flagged as an outlier relative to the stock's recent behavior."
            )

        if self._is_unrealistic_forecast(
            stock_series=stock_series,
            combined_prices=combined_prices,
            outlier_detected=outlier_detected,
        ):
            # Academic rule: when the raw forecast is too extreme, prefer the more conservative
            # component forecast instead of showing an unstable blend. This preserves the
            # model-driven workflow while avoiding clearly implausible outputs.
            fallback_applied = True
            fallback_reason = "Combined forecast exceeded realism thresholds; using conservative fallback."
            final_prices = self._build_conservative_fallback(
                stock_fourier_prices=stock_fourier_prices,
                index_based_prices=index_based_prices,
                alpha=alpha,
            )
            warnings.append(
                "Fallback logic replaced the raw combined forecast with a more conservative path."
            )

        confidence_score = self._calculate_confidence_score(
            correlation=correlation,
            alpha=alpha,
            benchmark_agreement_score=benchmark_agreement_score,
            recent_volatility=recent_volatility,
            outlier_detected=outlier_detected,
            fallback_applied=fallback_applied,
        )
        warning_status, level, title, message = self._build_warning_banner(
            confidence_score=confidence_score,
            outlier_detected=outlier_detected,
            fallback_applied=fallback_applied,
        )

        return ReliabilityAssessment(
            confidence_score=round(confidence_score, 4),
            warning_status=warning_status,
            warning_banner_level=level,
            warning_banner_title=title,
            warning_banner_message=message,
            warnings=warnings,
            outlier_detected=outlier_detected,
            outlier_score=round(outlier_score, 4),
            benchmark_agreement_score=round(benchmark_agreement_score, 4),
            recent_volatility=round(recent_volatility, 6),
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            final_prices=[round(float(price), 4) for price in final_prices],
        )

    def _calculate_agreement_score(
        self,
        stock_fourier_prices: list[float],
        index_based_prices: list[float],
        last_close: float,
    ) -> float:
        # Academic rule: when the two component forecasts disagree strongly, the model should be
        # treated as less reliable because the hybrid prediction depends on unstable components.
        absolute_differences = [
            abs(fourier_price - index_price)
            for fourier_price, index_price in zip(stock_fourier_prices, index_based_prices, strict=True)
        ]
        mean_difference_ratio = float(np.mean(absolute_differences)) / max(last_close, 0.01)
        return max(0.0, 1.0 - min(mean_difference_ratio / 0.15, 1.0))

    def _detect_outlier(
        self,
        stock_series: pd.Series,
        combined_prices: list[float],
        last_close: float,
    ) -> tuple[float, bool]:
        # Academic rule: compare the final predicted move against recent daily volatility. If the
        # move is many standard deviations larger than typical behavior, flag it as an outlier.
        recent_returns = stock_series.pct_change().dropna()
        if recent_returns.empty:
            return 0.0, False

        recent_std = float(recent_returns.tail(min(30, len(recent_returns))).std(ddof=0) or 0.0)
        if recent_std == 0:
            return 0.0, False

        terminal_return = (combined_prices[-1] - last_close) / max(last_close, 0.01)
        outlier_score = abs(terminal_return) / recent_std
        return outlier_score, outlier_score >= 3.5

    def _is_unrealistic_forecast(
        self,
        stock_series: pd.Series,
        combined_prices: list[float],
        outlier_detected: bool,
    ) -> bool:
        # Academic rule: apply a hard realism screen before exposing the forecast. A 2-week
        # prediction that implies extreme price appreciation or collapse is more likely to reflect
        # model instability than a believable short-horizon market move.
        last_close = float(stock_series.iloc[-1])
        terminal_change_ratio = abs((combined_prices[-1] - last_close) / max(last_close, 0.01))
        negative_or_zero_price = any(price <= 0 for price in combined_prices)
        return negative_or_zero_price or terminal_change_ratio > 0.35 or outlier_detected

    def _build_conservative_fallback(
        self,
        stock_fourier_prices: list[float],
        index_based_prices: list[float],
        alpha: float,
    ) -> list[float]:
        # Academic rule: during fallback, lean toward the more conservative component rather than
        # recomputing an unrelated model. This keeps the fallback interpretable and mathematically
        # tied to the existing model components.
        if alpha >= 0.5:
            return [min(fourier_price, index_price) for fourier_price, index_price in zip(stock_fourier_prices, index_based_prices, strict=True)]
        return list(index_based_prices)

    def _calculate_confidence_score(
        self,
        correlation: float,
        alpha: float,
        benchmark_agreement_score: float,
        recent_volatility: float,
        outlier_detected: bool,
        fallback_applied: bool,
    ) -> float:
        # Academic rule: the confidence score intentionally combines multiple interpretable factors
        # instead of using a black-box classifier. Stronger correlation and component agreement
        # increase confidence, while volatility, outlier flags, and fallback usage reduce it.
        correlation_component = max(correlation, 0.0)
        volatility_penalty = min(recent_volatility / 0.05, 1.0)

        score = (
            0.45 * correlation_component
            + 0.25 * alpha
            + 0.20 * benchmark_agreement_score
            + 0.10 * (1.0 - volatility_penalty)
        )

        if outlier_detected:
            score -= 0.25
        if fallback_applied:
            score -= 0.15

        return max(0.0, min(score, 1.0))

    def _build_warning_banner(
        self,
        confidence_score: float,
        outlier_detected: bool,
        fallback_applied: bool,
    ) -> tuple[str, str | None, str | None, str | None]:
        if fallback_applied:
            return (
                "high",
                "high",
                "Forecast Reliability Warning",
                "Fallback logic was applied because the raw forecast exceeded realism thresholds.",
            )
        if outlier_detected or confidence_score < 0.45:
            return (
                "medium",
                "medium",
                "Use Caution",
                "The model detected weaker reliability signals for this forecast horizon.",
            )
        if confidence_score < 0.65:
            return (
                "low",
                "low",
                "Moderate Confidence",
                "The model found a usable signal, but benchmark agreement or volatility reduced confidence.",
            )
        return ("normal", None, None, None)
