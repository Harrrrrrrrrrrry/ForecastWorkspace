from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class ForecastRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol.")
    horizon_days: int = Field(default=14, ge=1, le=30, description="Forecast horizon in trading days.")
    analysis_window_days: int = Field(
        default=180,
        ge=60,
        le=730,
        description="Number of trading days to use in the recent analysis window.",
    )
    analysis_end_date: str | None = Field(
        default=None,
        description="Optional YYYY-MM-DD date to cap the analysis window. Empty uses latest available data.",
    )

    @field_validator("analysis_end_date")
    @classmethod
    def validate_analysis_end_date(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None

        try:
            parsed_date = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("analysis_end_date must use YYYY-MM-DD format.") from exc

        if parsed_date > datetime.now(UTC).date():
            raise ValueError("analysis_end_date cannot be in the future.")

        return parsed_date.isoformat()


class PricePoint(BaseModel):
    date: str
    value: float


class StockHistoryPoint(BaseModel):
    date: str
    close: float


class StockHistoryResponse(BaseModel):
    ticker: str
    source: str = "yfinance"
    lookback_days: int
    points: list[StockHistoryPoint] = Field(default_factory=list)


class AnalysisWindow(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    lookback_days: int | None = None


class BenchmarkCandidate(BaseModel):
    symbol: str
    name: str
    correlation: float


class ModelDiagnostics(BaseModel):
    analysis_method: str
    selected_benchmark_symbol: str | None = None
    selected_benchmark_name: str | None = None
    selected_correlation: float | None = None
    stock_beta_to_benchmark: float | None = None
    projected_benchmark_daily_return: float | None = None
    fourier_harmonics_used: int | None = None
    benchmark_agreement_score: float | None = None
    recent_volatility: float | None = None
    forecast_outlier_score: float | None = None
    outlier_detected: bool = False
    fallback_applied: bool = False
    fallback_reason: str | None = None
    arima_order: str | None = None
    arima_status: str | None = None
    ml_model_name: str | None = None
    ml_status: str | None = None
    ml_training_samples: int | None = None
    ensemble_method: str | None = None


class WarningBanner(BaseModel):
    level: str
    title: str
    message: str


class ForecastSummary(BaseModel):
    selected_benchmark: str | None = None
    alpha: float | None = None
    current_price: float | None = None
    current_price_date: str | None = None
    predicted_price: float | None = None
    predicted_price_change: float | None = None
    predicted_percent_change: float | None = None
    confidence_score: float | None = None
    warning_status: str | None = None


class EnsembleComponent(BaseModel):
    model_id: str
    display_name: str
    weight: float
    terminal_price: float | None = None
    status: str
    detail: str | None = None


class FourierOverlay(BaseModel):
    trend_line: list[PricePoint] = Field(default_factory=list)
    fourier_model: list[PricePoint] = Field(default_factory=list)
    error_upper_bound: list[PricePoint] = Field(default_factory=list)
    error_lower_bound: list[PricePoint] = Field(default_factory=list)
    error_margin: float | None = None
    error_method: str | None = None


class ForecastResponse(BaseModel):
    ticker: str
    horizon_days: int
    analysis_window: AnalysisWindow
    historical_prices: list[PricePoint] = Field(default_factory=list)
    benchmark_candidates: list[BenchmarkCandidate] = Field(default_factory=list)
    selected_benchmark_history: list[PricePoint] = Field(default_factory=list)
    stock_fourier_forecast: list[PricePoint] = Field(default_factory=list)
    benchmark_projected_forecast: list[PricePoint] = Field(default_factory=list)
    index_based_forecast: list[PricePoint] = Field(default_factory=list)
    final_combined_forecast: list[PricePoint] = Field(default_factory=list)
    arima_forecast: list[PricePoint] = Field(default_factory=list)
    ml_forecast: list[PricePoint] = Field(default_factory=list)
    ensemble_forecast: list[PricePoint] = Field(default_factory=list)
    ensemble_components: list[EnsembleComponent] = Field(default_factory=list)
    fourier_overlay: FourierOverlay = Field(default_factory=FourierOverlay)
    diagnostics: ModelDiagnostics
    summary: ForecastSummary
    warning_banner: WarningBanner | None = None
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExplanationRequest(BaseModel):
    forecast: ForecastResponse


ExplanationSignal = Literal["bullish", "bearish", "neutral", "uncertain"]


class ExplanationResponse(BaseModel):
    model: str
    plain_language_explanation: str
    reliability_summary: str
    limitations_summary: str
    forecast_signal: ExplanationSignal
    disclaimer: str
