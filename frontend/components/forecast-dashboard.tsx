"use client";

import { ClipboardEvent, FormEvent, KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";

import { ForecastChart } from "@/components/forecast-chart";
import { LegalLinks } from "@/components/legal-links";
import { SiteHeader } from "@/components/site-header";
import {
  ExplanationResponse,
  ForecastResponse,
  fetchExplanation,
  fetchForecast,
} from "@/lib/api";

const DEFAULT_HORIZON = 14;
const DEFAULT_WINDOW = 180;

type ForecastProgressStatus =
  | "queued"
  | "getting_data"
  | "calculating_models"
  | "building_index_forecast"
  | "finalizing"
  | "complete"
  | "error";

type ForecastProgressItem = {
  ticker: string;
  status: ForecastProgressStatus;
  message: string;
  error: string | null;
};

type ForecastCardState = {
  ticker: string;
  forecast: ForecastResponse | null;
  error: string | null;
  explanation: ExplanationResponse | null;
  explanationError: string | null;
  isExplanationLoading: boolean;
};

export function ForecastDashboard() {
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [forecastDays, setForecastDays] = useState(`${DEFAULT_HORIZON}`);
  const [analysisWindowDays, setAnalysisWindowDays] = useState(`${DEFAULT_WINDOW}`);
  const [analysisEndDate, setAnalysisEndDate] = useState("");
  const [forecastCards, setForecastCards] = useState<ForecastCardState[]>([]);
  const [forecastProgressItems, setForecastProgressItems] = useState<ForecastProgressItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const progressTimersRef = useRef<number[]>([]);

  useEffect(() => {
    return () => {
      clearProgressTimers();
    };
  }, []);

  async function loadForecasts(
    tickers: string[],
    horizonDays: number,
    windowDays: number,
    windowEndDate: string,
  ) {
    clearProgressTimers();
    setIsLoading(true);
    setError(null);
    setForecastCards([]);
    setForecastProgressItems(
      tickers.map((ticker) => ({
        ticker,
        status: "queued",
        message: "Waiting to start",
        error: null,
      })),
    );

    const responses = await Promise.all(
      tickers.map(async (ticker) => {
        updateForecastProgress(ticker, "getting_data");
        scheduleProgressAdvance(ticker);

        try {
          const forecast = await fetchForecast(
            ticker,
            horizonDays,
            windowDays,
            windowEndDate || undefined,
          );
          updateForecastProgress(ticker, "complete");

          return {
            ticker,
            forecast,
            error: null,
            explanation: null,
            explanationError: null,
            isExplanationLoading: false,
          };
        } catch (requestError) {
          const message =
            requestError instanceof Error ? requestError.message : "Failed to load forecast.";
          updateForecastProgress(ticker, "error", message);

          return {
            ticker,
            forecast: null,
            error: message,
            explanation: null,
            explanationError: null,
            isExplanationLoading: false,
          };
        }
      }),
    );

    setForecastCards(responses);
    clearProgressTimers();
    setIsLoading(false);
  }

  function clearProgressTimers() {
    progressTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
    progressTimersRef.current = [];
  }

  function scheduleProgressAdvance(ticker: string) {
    const scheduledSteps: Array<{ delayMs: number; status: ForecastProgressStatus }> = [
      { delayMs: 700, status: "calculating_models" },
      { delayMs: 1800, status: "building_index_forecast" },
      { delayMs: 3200, status: "finalizing" },
    ];

    scheduledSteps.forEach(({ delayMs, status }) => {
      const timerId = window.setTimeout(() => {
        updateForecastProgress(ticker, status);
      }, delayMs);
      progressTimersRef.current.push(timerId);
    });
  }

  function updateForecastProgress(
    ticker: string,
    status: ForecastProgressStatus,
    statusError: string | null = null,
  ) {
    setForecastProgressItems((current) =>
      current.map((item) => {
        if (item.ticker !== ticker || isTerminalProgressStatus(item.status)) {
          return item;
        }

        return {
          ...item,
          status,
          message: getForecastProgressMessage(status),
          error: statusError,
        };
      }),
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const tickers = mergeTickers(selectedTickers, parseTickers(tickerInput));
    const parsedForecastDays = parsePositiveInteger(forecastDays);
    const parsedAnalysisWindowDays = parsePositiveInteger(analysisWindowDays);

    if (tickers.length === 0) {
      setError("Enter one or more ticker symbols.");
      setForecastCards([]);
      setForecastProgressItems([]);
      return;
    }

    if (parsedForecastDays == null || parsedAnalysisWindowDays == null) {
      setError("Forecast days and analysis window must be positive whole numbers.");
      setForecastProgressItems([]);
      return;
    }

    if (analysisEndDate && analysisEndDate > getTodayInputDate()) {
      setError("Window end date cannot be in the future.");
      setForecastProgressItems([]);
      return;
    }

    setSelectedTickers(tickers);
    setTickerInput("");
    await loadForecasts(
      tickers,
      parsedForecastDays,
      parsedAnalysisWindowDays,
      analysisEndDate,
    );
  }

  function handleTickerInputChange(value: string) {
    const parsedTickers = parseTickers(value);
    const shouldCommit = /[,\n;]$/.test(value);

    if (shouldCommit && parsedTickers.length > 0) {
      setSelectedTickers((current) => mergeTickers(current, parsedTickers));
      setTickerInput("");
      setError(null);
      return;
    }

    setTickerInput(value);
  }

  function handleTickerKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitTickerInput();
      return;
    }

    if (event.key === "Backspace" && tickerInput.length === 0 && selectedTickers.length > 0) {
      event.preventDefault();
      const nextTickers = selectedTickers.slice(0, -1);
      setSelectedTickers(nextTickers);
    }
  }

  function handleTickerPaste(event: ClipboardEvent<HTMLInputElement>) {
    const pastedText = event.clipboardData.getData("text");
    const parsedTickers = parseTickers(pastedText);

    if (parsedTickers.length === 0) {
      return;
    }

    event.preventDefault();
    setSelectedTickers((current) => mergeTickers(current, parsedTickers));
    setTickerInput("");
    setError(null);
  }

  function commitTickerInput() {
    const parsedTickers = parseTickers(tickerInput);
    if (parsedTickers.length === 0) {
      return;
    }

    setSelectedTickers((current) => mergeTickers(current, parsedTickers));
    setTickerInput("");
    setError(null);
  }

  function removeTicker(ticker: string) {
    setSelectedTickers((current) => current.filter((item) => item !== ticker));
  }

  async function handleGenerateExplanation(ticker: string) {
    const targetCard = forecastCards.find((card) => card.ticker === ticker);

    if (!targetCard?.forecast) {
      return;
    }

    setForecastCards((current) =>
      current.map((card) =>
        card.ticker === ticker
          ? {
              ...card,
              isExplanationLoading: true,
              explanationError: null,
            }
          : card,
      ),
    );

    try {
      const explanation = await fetchExplanation(targetCard.forecast);
      setForecastCards((current) =>
        current.map((card) =>
          card.ticker === ticker
            ? {
                ...card,
                explanation,
                explanationError: null,
                isExplanationLoading: false,
              }
            : card,
        ),
      );
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Failed to generate explanation.";
      setForecastCards((current) =>
        current.map((card) =>
          card.ticker === ticker
            ? {
                ...card,
                explanationError: message,
                isExplanationLoading: false,
              }
            : card,
        ),
      );
    }
  }

  const successfulCount = forecastCards.filter((item) => item.forecast).length;

  return (
    <main className="mission-shell dashboard-shell">
      <section className="scene scene-hero">
        <div className="scene-overlay" />
        <SiteHeader />

        <div className="hero-layout">
          <div className="hero-copy">
            <h1>Try a forecast for any stock.</h1>
            <p>
              Enter multiple ticker symbols to generate a dedicated forecast board for each stock
              with charts, model diagnostics, and benchmark comparison.
            </p>

            <form className="hero-form" onSubmit={handleSubmit}>
              <label className="field-block">
                <span className="field-label">Tickers</span>
                <div className="ticker-input-shell">
                  <div className="ticker-chip-list">
                    {selectedTickers.map((ticker) => (
                      <span className="ticker-chip" key={ticker}>
                        <span>{ticker}</span>
                        <button
                          aria-label={`Remove ${ticker}`}
                          className="ticker-chip-remove"
                          onClick={() => removeTicker(ticker)}
                          type="button"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                    <input
                      className="ticker-input"
                      name="tickers"
                      onChange={(event) => handleTickerInputChange(event.target.value)}
                      onKeyDown={handleTickerKeyDown}
                      onPaste={handleTickerPaste}
                      placeholder={selectedTickers.length === 0 ? "Type ticker and press Enter" : "Add ticker"}
                      value={tickerInput}
                    />
                  </div>
                </div>
              </label>

              <div className="parameter-grid">
                <label className="field-block">
                  <span className="field-label">Forecast days</span>
                  <input
                    className="parameter-input"
                    inputMode="numeric"
                    min="1"
                    name="forecastDays"
                    onChange={(event) => setForecastDays(event.target.value)}
                    placeholder="14"
                    type="number"
                    value={forecastDays}
                  />
                </label>

                <label className="field-block">
                  <span className="field-label">Analysis window</span>
                  <input
                    className="parameter-input"
                    inputMode="numeric"
                    min="1"
                    name="analysisWindowDays"
                    onChange={(event) => setAnalysisWindowDays(event.target.value)}
                    placeholder="180"
                    type="number"
                    value={analysisWindowDays}
                  />
                </label>

                <label className="field-block">
                  <span className="field-label">Window end date</span>
                  <input
                    className="parameter-input"
                    max={getTodayInputDate()}
                    name="analysisEndDate"
                    onChange={(event) => setAnalysisEndDate(event.target.value)}
                    type="date"
                    value={analysisEndDate}
                  />
                </label>
              </div>

              <div className="hero-actions">
                <button className="forecast-submit-button" disabled={isLoading} type="submit">
                  {isLoading ? "Running forecasts" : "Run forecasts"}
                </button>
                <div className="hero-status-row" aria-label="Forecast request status">
                  <span className="hero-status-pill">
                    <span>Requested</span>
                    <strong>{selectedTickers.length}</strong>
                  </span>
                  <span className="hero-status-pill hero-status-pill-success">
                    <span>Success</span>
                    <strong>{successfulCount}</strong>
                  </span>
                </div>
                <span className="hero-meta">
                  Press Enter or comma to add tickers. Window {analysisWindowDays || "--"} days /
                  End {analysisEndDate || "latest available"} / Horizon {forecastDays || "--"} days
                </span>
              </div>
            </form>

            {forecastProgressItems.length > 0 ? (
              <ForecastProgressPanel items={forecastProgressItems} />
            ) : null}

            {error ? <div className="system-warning">{error}</div> : null}
            {forecastCards.length > 0 ? (
              <div className="stocks-nav">
                {forecastCards.map((item) => (
                  <a className="stock-chip" href={`#stock-${item.ticker}`} key={item.ticker}>
                    {item.ticker}
                  </a>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="scene scene-results">
        <div className="scene-overlay scene-overlay-soft" />
        <div className="stocks-stack">
          {forecastCards.map((item) => (
            <StockForecastBoard
              item={item}
              key={item.ticker}
              onGenerateExplanation={handleGenerateExplanation}
            />
          ))}

          {!isLoading && forecastCards.length === 0 ? (
            <div className="empty-results">
              <strong>No stock boards yet</strong>
              <p>Enter one or more ticker symbols to generate forecast boards.</p>
            </div>
          ) : null}
        </div>
      </section>

      <LegalLinks />
    </main>
  );
}

function ForecastProgressPanel({ items }: { items: ForecastProgressItem[] }) {
  const completeCount = items.filter((item) => item.status === "complete").length;
  const errorCount = items.filter((item) => item.status === "error").length;
  const totalCount = items.length;

  return (
    <section className="forecast-progress-panel" aria-label="Forecast run progress">
      <div className="forecast-progress-header">
        <div>
          <span className="scene-kicker">Run progress</span>
          <h2>Forecast pipeline</h2>
        </div>
        <span className="forecast-progress-summary">
          {completeCount}/{totalCount} complete
          {errorCount > 0 ? ` / ${errorCount} error${errorCount === 1 ? "" : "s"}` : ""}
        </span>
      </div>

      <div className="forecast-progress-list">
        {items.map((item) => (
          <div
            className={`forecast-progress-row forecast-progress-row-${item.status}`}
            key={item.ticker}
          >
            <span className="forecast-progress-dot" aria-hidden="true" />
            <span className="forecast-progress-ticker">{item.ticker}</span>
            <span className="forecast-progress-step">
              {getForecastProgressLabel(item.status)}
            </span>
            <span className="forecast-progress-message">{item.error ?? item.message}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function StockForecastBoard({
  item,
  onGenerateExplanation,
}: {
  item: ForecastCardState;
  onGenerateExplanation: (ticker: string) => void;
}) {
  const forecast = item.forecast;
  const summary = forecast?.summary;
  const diagnostics = forecast?.diagnostics;
  const warningBanner = forecast?.warning_banner;
  const projectedChangeTone = getDirectionalTone(summary?.predicted_price_change);

  return (
    <article className="stock-board" id={`stock-${item.ticker}`}>
      <div className="stock-board-header">
        <div>
          <h2 className="stock-board-title">{item.ticker} Forecast</h2>
          <p className="stock-board-meta">
            {forecast
              ? `Analysis window ${formatAnalysisWindow(forecast)} / Forecast horizon ${forecast.horizon_days} days`
              : "Forecast data could not be loaded for this ticker."}
          </p>
        </div>
      </div>

      {item.error ? (
        <div className="stock-board-content">
          <div className="system-warning">
            <strong>Forecast error</strong>
            <span>{item.error}</span>
          </div>
        </div>
      ) : forecast ? (
        <div className="stock-board-content">
          {warningBanner ? (
            <div className="system-warning">
              <strong>{warningBanner.title}</strong>
              <span>{warningBanner.message}</span>
            </div>
          ) : null}

          <div className="summary-grid summary-grid-primary">
            <SummaryCard
              detail={
                summary?.current_price_date
                  ? `As of ${summary.current_price_date}`
                  : "Latest available daily close"
              }
              emphasis="key"
              label="Latest Close"
              value={formatCurrency(summary?.current_price)}
            />
            <SummaryCard
              detail={`End of ${forecast.horizon_days}-day forecast horizon`}
              emphasis="key"
              label="Forecast Terminal Price"
              value={formatCurrency(summary?.predicted_price)}
            />
            <SummaryCard
              emphasis="key"
              label="Projected Change"
              tone={projectedChangeTone}
              value={formatProjectedChange(
                summary?.predicted_price_change,
                summary?.predicted_percent_change,
              )}
            />
          </div>

          <ForecastChart forecast={forecast} />

          <div className="notes-grid">
            <section className="notes-block">
              <span className="scene-kicker notes-title">Diagnostics</span>
              <ul className="signal-list">
                <li>Analysis method: {diagnostics?.analysis_method ?? "Unavailable"}</li>
                <li>Alpha weight: {formatDecimal(summary?.alpha)}</li>
                <li>Fourier harmonics: {formatInteger(diagnostics?.fourier_harmonics_used)}</li>
                <li>ARIMA order: {diagnostics?.arima_order ?? "Unavailable"}</li>
                <li>ML samples: {formatInteger(diagnostics?.ml_training_samples)}</li>
                <li>Combination method: {diagnostics?.ensemble_method ?? "Unavailable"}</li>
              </ul>
            </section>

            <section className="notes-block explanation-notes-block">
              <span className="scene-kicker notes-title">GPT 5.4</span>
              <div className="explanation-shell">
                <p className="notes-copy">
                  GPT checks the forecast. AI can make mistakes.
                </p>
                <div className="explanation-actions">
                  <button
                    className="ghost-button"
                    disabled={item.isExplanationLoading}
                    onClick={() => onGenerateExplanation(item.ticker)}
                    type="button"
                  >
                    {item.isExplanationLoading ? "Asking" : "Ask GPT"}
                  </button>
                  {item.explanation ? (
                    <span className="explanation-meta">Model {item.explanation.model}</span>
                  ) : null}
                </div>
                {item.explanationError ? (
                  <div className="system-warning">
                    <strong>Explanation error</strong>
                    <span>{item.explanationError}</span>
                  </div>
                ) : null}
                {item.explanation ? (
                  <div className="explanation-result">
                    <article className="explanation-section">
                      <strong>AI Verdict</strong>
                      <div className="ai-verdict-row">
                        <span
                          className={`ai-confidence-score ${getAiConfidenceClassName(
                            item.explanation.ai_confidence_percent,
                          )}`}
                        >
                          {item.explanation.ai_confidence_percent}%
                        </span>
                        <p>{renderBoldNumbers(item.explanation.ai_verdict)}</p>
                      </div>
                    </article>
                    <article className="explanation-section">
                      <strong>Why</strong>
                      <p>{renderBoldNumbers(item.explanation.reasoning_summary)}</p>
                    </article>
                  </div>
                ) : null}
              </div>
            </section>
          </div>
        </div>
      ) : null}
    </article>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  tone = "default",
  emphasis = "standard",
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "positive" | "negative" | "neutral";
  emphasis?: "standard" | "key";
}) {
  const cardClassName = [
    "summary-card",
    emphasis === "key" ? "summary-card-key" : "",
    tone !== "default" ? `summary-card-${tone}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const valueClassName = [
    "summary-value",
    emphasis === "key" ? "summary-value-key" : "",
    tone !== "default" ? `summary-value-${tone}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cardClassName}>
      <span className="summary-label">{label}</span>
      <span className={valueClassName}>{value}</span>
      {detail ? <span className="summary-detail">{detail}</span> : null}
    </div>
  );
}

function parseTickers(input: string): string[] {
  const seen = new Set<string>();

  return input
    .split(/[\s,;]+/)
    .map((ticker) => ticker.trim().toUpperCase())
    .filter((ticker) => ticker.length > 0)
    .filter((ticker) => {
      if (seen.has(ticker)) {
        return false;
      }

      seen.add(ticker);
      return true;
    });
}

function mergeTickers(existing: string[], incoming: string[]): string[] {
  const seen = new Set<string>();

  return [...existing, ...incoming].filter((ticker) => {
    if (seen.has(ticker)) {
      return false;
    }

    seen.add(ticker);
    return true;
  });
}

function isTerminalProgressStatus(status: ForecastProgressStatus): boolean {
  return status === "complete" || status === "error";
}

function getForecastProgressLabel(status: ForecastProgressStatus): string {
  const labels: Record<ForecastProgressStatus, string> = {
    queued: "Queued",
    getting_data: "Getting data",
    calculating_models: "Calculating models",
    building_index_forecast: "Index / benchmark forecast",
    finalizing: "Finalizing output",
    complete: "Complete",
    error: "Error",
  };

  return labels[status];
}

function getForecastProgressMessage(status: ForecastProgressStatus): string {
  const messages: Record<ForecastProgressStatus, string> = {
    queued: "Waiting to start",
    getting_data: "Requesting historical prices and benchmark candidates",
    calculating_models: "Preparing model forecasts and diagnostics",
    building_index_forecast: "Comparing market index movement with the stock",
    finalizing: "Combining model outputs and reliability checks",
    complete: "Forecast board is ready",
    error: "Forecast request failed",
  };

  return messages[status];
}

function parsePositiveInteger(value: string): number | null {
  const parsed = Number.parseInt(value, 10);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
}

function getTodayInputDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function findWeight(forecast: ForecastResponse | null, modelId: string): number | null {
  return (
    forecast?.ensemble_components.find((component) => component.model_id === modelId)?.weight ??
    null
  );
}

function formatAnalysisWindow(forecast: ForecastResponse): string {
  const start = forecast.analysis_window.start_date ?? "Unknown start";
  const end = forecast.analysis_window.end_date ?? "Unknown end";
  return `${start} to ${end}`;
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value.toFixed(2)} USD`;
}

function formatSignedCurrency(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value >= 0 ? "+" : ""}${value.toFixed(2)} USD`;
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatScore(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return value.toFixed(4);
}

function formatWeight(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${(value * 100).toFixed(1)}%`;
}

function formatDecimal(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return value.toFixed(4);
}

function formatProjectedChange(
  priceChange: number | null | undefined,
  percentChange: number | null | undefined,
): string {
  if (priceChange == null && percentChange == null) {
    return "Unavailable";
  }

  if (priceChange == null) {
    return formatPercent(percentChange);
  }

  if (percentChange == null) {
    return formatSignedCurrency(priceChange);
  }

  return `${formatSignedCurrency(priceChange)} (${formatPercent(percentChange)})`;
}

function getDirectionalTone(
  value: number | null | undefined,
): "neutral" | "positive" | "negative" {
  if (value == null || value === 0) {
    return "neutral";
  }

  return value > 0 ? "positive" : "negative";
}

function getAiConfidenceClassName(value: number): string {
  if (value < 30) {
    return "ai-confidence-danger";
  }

  if (value < 60) {
    return "ai-confidence-warning";
  }

  if (value < 80) {
    return "ai-confidence-moderate";
  }

  return "ai-confidence-strong";
}

function renderBoldNumbers(text: string): ReactNode[] {
  const numericPattern =
    /([+-]?\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s?(?:USD|usd|%))?|[+-]?\d+(?:\.\d+)?(?:\s?(?:USD|usd|%))?)/g;
  const parts: ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(numericPattern)) {
    const matchText = match[0];
    const matchIndex = match.index ?? 0;

    if (matchIndex > lastIndex) {
      parts.push(text.slice(lastIndex, matchIndex));
    }

    parts.push(<strong key={`${matchText}-${matchIndex}`}>{matchText}</strong>);
    lastIndex = matchIndex + matchText.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function formatInteger(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value}`;
}
