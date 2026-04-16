from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SupplementalForecastResult:
    model_id: str
    display_name: str
    forecast_values: list[float]
    status: str
    detail: str | None = None
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == "active" and bool(self.forecast_values)


@dataclass
class EnsembleComponentResult:
    model_id: str
    display_name: str
    weight: float
    terminal_price: float | None
    status: str
    detail: str | None = None


@dataclass
class EnsembleForecastResult:
    forecast_values: list[float]
    components: list[EnsembleComponentResult]
    method: str


class EnsembleForecastService:
    """Blend the core forecast with any available supplemental model curves."""

    def build(
        self,
        core_prices: list[float],
        arima_result: SupplementalForecastResult,
        ml_result: SupplementalForecastResult,
        core_confidence: float,
    ) -> EnsembleForecastResult:
        model_results = {
            "market_influence": SupplementalForecastResult(
                model_id="market_influence",
                display_name="Market Influence Model",
                forecast_values=core_prices,
                status="active",
                metadata={"confidence_score": round(core_confidence, 4)},
            ),
            arima_result.model_id: arima_result,
            ml_result.model_id: ml_result,
        }

        base_weights = {
            "market_influence": self._core_weight(core_confidence),
            "arima": 0.25,
            "xgboost": 0.25,
        }

        active_weights = {
            model_id: base_weights.get(model_id, 0.0)
            for model_id, result in model_results.items()
            if result.is_active
        }
        normalized_weights = self._normalize_weights(active_weights)

        if not normalized_weights:
            normalized_weights = {"market_influence": 1.0}

        horizon_days = len(core_prices)
        blended_values: list[float] = []
        for index in range(horizon_days):
            weighted_value = sum(
                normalized_weights[model_id] * model_results[model_id].forecast_values[index]
                for model_id in normalized_weights
            )
            blended_values.append(round(float(weighted_value), 4))

        components = [
            EnsembleComponentResult(
                model_id=result.model_id,
                display_name=result.display_name,
                weight=round(normalized_weights.get(model_id, 0.0), 4),
                terminal_price=(
                    round(float(result.forecast_values[-1]), 4) if result.forecast_values else None
                ),
                status=result.status,
                detail=result.detail,
            )
            for model_id, result in model_results.items()
        ]

        return EnsembleForecastResult(
            forecast_values=blended_values,
            components=components,
            method="Weighted ensemble of Market Influence, ARIMA, and local XGBoost forecasts.",
        )

    def _core_weight(self, core_confidence: float) -> float:
        if core_confidence >= 0.7:
            return 0.5
        if core_confidence >= 0.45:
            return 0.45
        return 0.4

    def _normalize_weights(self, weights: dict[str, float]) -> dict[str, float]:
        total_weight = sum(weights.values())
        if total_weight <= 0:
            return {}
        return {
            model_id: weight / total_weight
            for model_id, weight in weights.items()
        }
