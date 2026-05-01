const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEFAULT_FORECAST_REQUEST_TIMEOUT_MS = 120_000;
const FORECAST_REQUEST_TIMEOUT_MS = parseForecastTimeout(
  process.env.NEXT_PUBLIC_FORECAST_REQUEST_TIMEOUT_MS,
);

function parseForecastTimeout(value: string | undefined): number {
  if (!value) {
    return DEFAULT_FORECAST_REQUEST_TIMEOUT_MS;
  }

  const parsedValue = Number.parseInt(value, 10);
  return Number.isFinite(parsedValue) && parsedValue > 0
    ? parsedValue
    : DEFAULT_FORECAST_REQUEST_TIMEOUT_MS;
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  timeoutMs: number,
  timeoutMessage: string,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(timeoutMessage);
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function readErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const errorPayload = (await response.json()) as { detail?: string };
    if (errorPayload.detail) {
      return errorPayload.detail;
    }
  } catch {
    // Use the fallback when the response body is not JSON.
  }

  return fallbackMessage;
}

export type PricePoint = {
  date: string;
  value: number;
};

export type StockHistoryPoint = {
  date: string;
  close: number;
};

export type StockHistoryResponse = {
  ticker: string;
  source: string;
  lookback_days: number;
  points: StockHistoryPoint[];
};

export type AnalysisWindow = {
  start_date: string | null;
  end_date: string | null;
  lookback_days: number | null;
};

export type BenchmarkCandidate = {
  symbol: string;
  name: string;
  correlation: number;
};

export type WarningBanner = {
  level: string;
  title: string;
  message: string;
};

export type ForecastSummary = {
  selected_benchmark: string | null;
  alpha: number | null;
  current_price: number | null;
  current_price_date: string | null;
  predicted_price: number | null;
  predicted_price_change: number | null;
  predicted_percent_change: number | null;
  confidence_score: number | null;
  warning_status: string | null;
};

export type ModelDiagnostics = {
  analysis_method: string;
  selected_benchmark_symbol?: string | null;
  selected_benchmark_name?: string | null;
  selected_correlation?: number | null;
  stock_beta_to_benchmark?: number | null;
  projected_benchmark_daily_return?: number | null;
  fourier_harmonics_used?: number | null;
  benchmark_agreement_score?: number | null;
  recent_volatility?: number | null;
  forecast_outlier_score?: number | null;
  outlier_detected: boolean;
  fallback_applied: boolean;
  fallback_reason?: string | null;
  arima_order?: string | null;
  arima_status?: string | null;
  ml_model_name?: string | null;
  ml_status?: string | null;
  ml_training_samples?: number | null;
  ensemble_method?: string | null;
};

export type EnsembleComponent = {
  model_id: string;
  display_name: string;
  weight: number;
  terminal_price: number | null;
  status: string;
  detail?: string | null;
};

export type FourierOverlay = {
  trend_line: PricePoint[];
  fourier_model: PricePoint[];
  error_upper_bound: PricePoint[];
  error_lower_bound: PricePoint[];
  error_margin: number | null;
  error_method: string | null;
};

export type ForecastResponse = {
  ticker: string;
  horizon_days: number;
  analysis_window: AnalysisWindow;
  historical_prices: PricePoint[];
  benchmark_candidates: BenchmarkCandidate[];
  selected_benchmark_history: PricePoint[];
  stock_fourier_forecast: PricePoint[];
  benchmark_projected_forecast: PricePoint[];
  index_based_forecast: PricePoint[];
  final_combined_forecast: PricePoint[];
  arima_forecast: PricePoint[];
  ml_forecast: PricePoint[];
  ensemble_forecast: PricePoint[];
  ensemble_components: EnsembleComponent[];
  fourier_overlay: FourierOverlay;
  diagnostics: ModelDiagnostics;
  summary: ForecastSummary;
  warning_banner: WarningBanner | null;
  warnings: string[];
  limitations: string[];
};

export type ExplanationResponse = {
  model: string;
  ai_confidence_percent: number;
  ai_verdict: string;
  reasoning_summary: string;
  forecast_signal: "bullish" | "bearish" | "neutral" | "uncertain";
};

const LOCAL_EXPLANATION_CONFIDENCE_BY_TICKER: Record<string, number> = {
  GME: 29,
  TSLA: 45,
  NVDA: 72,
  AAPL: 88,
};

export async function fetchStockHistory(
  ticker: string,
  lookbackDays = 180,
): Promise<StockHistoryResponse> {
  const encodedTicker = encodeURIComponent(ticker.trim().toUpperCase());
  const response = await fetch(
    `${API_BASE_URL}/stocks/${encodedTicker}/history?lookback_days=${lookbackDays}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `History request failed with status ${response.status}`));
  }

  return (await response.json()) as StockHistoryResponse;
}

export async function fetchForecast(
  ticker: string,
  horizonDays = 14,
  analysisWindowDays = 180,
  analysisEndDate?: string,
): Promise<ForecastResponse> {
  const requestBody: {
    ticker: string;
    horizon_days: number;
    analysis_window_days: number;
    analysis_end_date?: string;
  } = {
    ticker: ticker.trim().toUpperCase(),
    horizon_days: horizonDays,
    analysis_window_days: analysisWindowDays,
  };

  if (analysisEndDate) {
    requestBody.analysis_end_date = analysisEndDate;
  }

  const response = await fetchWithTimeout(
    `${API_BASE_URL}/forecast`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
      body: JSON.stringify(requestBody),
    },
    FORECAST_REQUEST_TIMEOUT_MS,
    `Forecast request timed out after ${Math.round(FORECAST_REQUEST_TIMEOUT_MS / 1000)} seconds. Please try again.`,
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Forecast request failed with status ${response.status}`));
  }

  return (await response.json()) as ForecastResponse;
}

export async function fetchExplanation(forecast: ForecastResponse): Promise<ExplanationResponse> {
  if (shouldUseLocalExplanationMock()) {
    return buildLocalExplanationMock(forecast);
  }

  const response = await fetch(`${API_BASE_URL}/explanations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify({
      forecast,
    }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Explanation request failed with status ${response.status}`));
  }

  return (await response.json()) as ExplanationResponse;
}

function shouldUseLocalExplanationMock(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
}

function buildLocalExplanationMock(forecast: ForecastResponse): ExplanationResponse {
  const ticker = forecast.ticker.toUpperCase();
  const confidencePercent =
    LOCAL_EXPLANATION_CONFIDENCE_BY_TICKER[ticker] ??
    clampPercent(Math.round((forecast.summary.confidence_score ?? 0.72) * 100));
  const predictedPrice = formatMockCurrency(forecast.summary.predicted_price);
  const predictedChange = formatMockPercent(forecast.summary.predicted_percent_change);

  return {
    model: "local-mock",
    ai_confidence_percent: confidencePercent,
    ai_verdict: buildMockVerdict(confidencePercent, predictedPrice, predictedChange),
    reasoning_summary: buildMockReasoning(forecast, confidencePercent),
    forecast_signal: confidencePercent < 30 ? "uncertain" : getMockForecastSignal(forecast),
  };
}

function buildMockVerdict(
  confidencePercent: number,
  predictedPrice: string,
  predictedChange: string,
): string {
  if (confidencePercent < 30) {
    return `I would be skeptical of the ${predictedPrice} forecast and the ${predictedChange} move.`;
  }

  if (confidencePercent < 60) {
    return `I would not fully trust the exact ${predictedPrice} price target, even though the ${predictedChange} move is usable for review.`;
  }

  if (confidencePercent < 80) {
    return `I would moderately trust the ${predictedPrice} forecast, with ${predictedChange} still carrying model risk.`;
  }

  return `I would treat the ${predictedPrice} forecast as reasonably believable, including the ${predictedChange} move.`;
}

function buildMockReasoning(forecast: ForecastResponse, confidencePercent: number): string {
  const agreement = formatMockNumber(forecast.diagnostics.benchmark_agreement_score);
  const volatility = formatMockNumber(forecast.diagnostics.recent_volatility);

  return `This local mock gives ${confidencePercent}% AI confidence from benchmark agreement ${agreement} and volatility ${volatility}. It is only for UI testing and is not financial advice.`;
}

function getMockForecastSignal(
  forecast: ForecastResponse,
): "bullish" | "bearish" | "neutral" | "uncertain" {
  const percentChange = forecast.summary.predicted_percent_change;

  if (percentChange == null || Math.abs(percentChange) < 0.1) {
    return "neutral";
  }

  return percentChange > 0 ? "bullish" : "bearish";
}

function formatMockCurrency(value: number | null): string {
  return value == null ? "the terminal price" : `${value.toFixed(2)} USD`;
}

function formatMockPercent(value: number | null): string {
  return value == null ? "projected percent" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatMockNumber(value: number | null | undefined): string {
  return value == null ? "unavailable" : value.toFixed(4);
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
