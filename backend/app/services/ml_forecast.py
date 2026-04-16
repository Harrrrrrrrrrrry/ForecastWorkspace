from __future__ import annotations

import pandas as pd

from app.services.ensemble import SupplementalForecastResult


class XGBoostForecastService:
    """Train a lightweight local boosting model on lagged return features."""

    def __init__(self, stock_lags: int = 5, benchmark_lags: int = 3) -> None:
        self.stock_lags = stock_lags
        self.benchmark_lags = benchmark_lags

    def forecast(
        self,
        stock_series: pd.Series,
        benchmark_series: pd.Series,
        horizon_days: int,
        projected_benchmark_return: float,
    ) -> SupplementalForecastResult:
        try:
            from xgboost import XGBRegressor
        except Exception as exc:
            return SupplementalForecastResult(
                model_id="xgboost",
                display_name="Local XGBoost",
                forecast_values=[],
                status="unavailable",
                detail=f"XGBoost is unavailable: {exc}",
            )

        training_frame = self._build_training_frame(stock_series, benchmark_series)
        if len(training_frame) < 30:
            return SupplementalForecastResult(
                model_id="xgboost",
                display_name="Local XGBoost",
                forecast_values=[],
                status="unavailable",
                detail="XGBoost requires at least 30 training rows after feature generation.",
            )

        feature_columns = [column for column in training_frame.columns if column != "target_return"]
        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=160,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        try:
            model.fit(training_frame[feature_columns], training_frame["target_return"])
        except Exception as exc:
            return SupplementalForecastResult(
                model_id="xgboost",
                display_name="Local XGBoost",
                forecast_values=[],
                status="unavailable",
                detail=f"XGBoost training failed: {exc}",
            )

        stock_return_history = training_frame["stock_return"].tolist()
        benchmark_return_history = training_frame["benchmark_return"].tolist()

        current_price = float(stock_series.iloc[-1])
        forecast_values: list[float] = []

        for _ in range(horizon_days):
            benchmark_return_history.append(projected_benchmark_return)
            feature_row = self._build_feature_row(
                stock_return_history=stock_return_history,
                benchmark_return_history=benchmark_return_history,
            )
            try:
                predicted_return = float(model.predict(pd.DataFrame([feature_row]))[0])
            except Exception as exc:
                return SupplementalForecastResult(
                    model_id="xgboost",
                    display_name="Local XGBoost",
                    forecast_values=[],
                    status="unavailable",
                    detail=f"XGBoost inference failed: {exc}",
                )
            stock_return_history.append(predicted_return)

            current_price *= 1.0 + predicted_return
            current_price = max(current_price, 0.01)
            forecast_values.append(round(current_price, 4))

        return SupplementalForecastResult(
            model_id="xgboost",
            display_name="Local XGBoost",
            forecast_values=forecast_values,
            status="active",
            metadata={
                "training_samples": len(training_frame),
                "feature_count": len(feature_columns),
            },
        )

    def _build_training_frame(self, stock_series: pd.Series, benchmark_series: pd.Series) -> pd.DataFrame:
        aligned = pd.concat(
            [
                stock_series.astype(float).pct_change().rename("stock_return"),
                benchmark_series.astype(float).pct_change().rename("benchmark_return"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        for lag in range(1, self.stock_lags + 1):
            aligned[f"stock_return_lag_{lag}"] = aligned["stock_return"].shift(lag)

        for lag in range(1, self.benchmark_lags + 1):
            aligned[f"benchmark_return_lag_{lag}"] = aligned["benchmark_return"].shift(lag)

        aligned["stock_return_mean_5"] = aligned["stock_return"].rolling(5).mean()
        aligned["stock_return_std_5"] = aligned["stock_return"].rolling(5).std(ddof=0)
        aligned["benchmark_return_mean_5"] = aligned["benchmark_return"].rolling(5).mean()
        aligned["benchmark_return_std_5"] = aligned["benchmark_return"].rolling(5).std(ddof=0)
        aligned["target_return"] = aligned["stock_return"].shift(-1)

        return aligned.dropna().copy()

    def _build_feature_row(
        self,
        stock_return_history: list[float],
        benchmark_return_history: list[float],
    ) -> dict[str, float]:
        feature_row: dict[str, float] = {
            "stock_return": float(stock_return_history[-1]),
            "benchmark_return": float(benchmark_return_history[-1]),
        }

        for lag in range(1, self.stock_lags + 1):
            feature_row[f"stock_return_lag_{lag}"] = float(stock_return_history[-lag])

        for lag in range(1, self.benchmark_lags + 1):
            feature_row[f"benchmark_return_lag_{lag}"] = float(benchmark_return_history[-lag])

        feature_row["stock_return_mean_5"] = float(sum(stock_return_history[-5:]) / 5)
        feature_row["stock_return_std_5"] = float(pd.Series(stock_return_history[-5:]).std(ddof=0))
        feature_row["benchmark_return_mean_5"] = float(sum(benchmark_return_history[-5:]) / 5)
        feature_row["benchmark_return_std_5"] = float(
            pd.Series(benchmark_return_history[-5:]).std(ddof=0)
        )

        return feature_row
