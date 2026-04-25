"use client";

import Link from "next/link";
import { ClipboardEvent, FormEvent, KeyboardEvent, useEffect, useState } from "react";

import { ForecastChart } from "@/components/forecast-chart";
import {
  AuthUser,
  ExplanationResponse,
  ForecastResponse,
  fetchCurrentUser,
  fetchExplanation,
  fetchForecast,
} from "@/lib/api";
import {
  AUTH_STATE_EVENT,
  clearStoredAuthSession,
  getStoredAuthToken,
  updateStoredAuthUser,
} from "@/lib/auth";

const DEFAULT_HORIZON = 14;
const DEFAULT_WINDOW = 180;

type ForecastCardState = {
  ticker: string;
  forecast: ForecastResponse | null;
  error: string | null;
  explanation: ExplanationResponse | null;
  explanationError: string | null;
  isExplanationLoading: boolean;
};

export function ForecastDashboard() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [forecastDays, setForecastDays] = useState(`${DEFAULT_HORIZON}`);
  const [analysisWindowDays, setAnalysisWindowDays] = useState(`${DEFAULT_WINDOW}`);
  const [forecastCards, setForecastCards] = useState<ForecastCardState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function hydrateAuthState() {
      const token = getStoredAuthToken();

      if (!token) {
        if (isActive) {
          setCurrentUser(null);
          setAuthToken(null);
          setForecastCards([]);
          setError(null);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(token);
        if (!isActive) {
          return;
        }

        updateStoredAuthUser(user);
        setCurrentUser(user);
        setAuthToken(token);
      } catch {
        if (!isActive) {
          return;
        }

        clearStoredAuthSession();
        setCurrentUser(null);
        setAuthToken(null);
        setForecastCards([]);
      }
    }

    function handleAuthStateChange() {
      void hydrateAuthState();
    }

    void hydrateAuthState();
    window.addEventListener(AUTH_STATE_EVENT, handleAuthStateChange);

    return () => {
      isActive = false;
      window.removeEventListener(AUTH_STATE_EVENT, handleAuthStateChange);
    };
  }, []);

  async function loadForecasts(
    token: string,
    tickers: string[],
    horizonDays: number,
    windowDays: number,
  ) {
    setIsLoading(true);
    setError(null);

    const responses = await Promise.all(
      tickers.map(async (ticker) => {
        try {
          const forecast = await fetchForecast(ticker, token, horizonDays, windowDays);
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
    setIsLoading(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const tickers = mergeTickers(selectedTickers, parseTickers(tickerInput));
    const parsedForecastDays = parsePositiveInteger(forecastDays);
    const parsedAnalysisWindowDays = parsePositiveInteger(analysisWindowDays);

    if (tickers.length === 0) {
      setError("Enter one or more ticker symbols.");
      setForecastCards([]);
      return;
    }

    if (parsedForecastDays == null || parsedAnalysisWindowDays == null) {
      setError("Forecast days and analysis window must be positive whole numbers.");
      return;
    }

    if (!authToken) {
      setError("Sign in to run forecasts and GPT explanations.");
      return;
    }

    setSelectedTickers(tickers);
    setTickerInput("");
    await loadForecasts(authToken, tickers, parsedForecastDays, parsedAnalysisWindowDays);
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

  function handleSignOut() {
    clearStoredAuthSession();
    setCurrentUser(null);
    setAuthToken(null);
    setForecastCards([]);
    setError(null);
  }

  async function handleGenerateExplanation(ticker: string) {
    const targetCard = forecastCards.find((card) => card.ticker === ticker);

    if (!authToken || !targetCard?.forecast) {
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
      const explanation = await fetchExplanation(targetCard.forecast, authToken);
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
  const failedCount = forecastCards.filter((item) => item.error).length;

  return (
    <main className="mission-shell dashboard-shell">
      <section className="scene scene-hero">
        <div className="scene-overlay" />
        <header className="mission-nav">
          <Link className="nav-mark" href="/">
            Forecast Workspace
          </Link>
          <div className="nav-links">
            <Link href="/">Home</Link>
            {currentUser ? (
              <>
                <span className="nav-user">
                  {currentUser.full_name?.trim() || currentUser.email}
                  <span className="nav-user-role">{currentUser.role}</span>
                </span>
                <button className="nav-link-button" onClick={handleSignOut} type="button">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link href="/sign-in">Sign In</Link>
                <Link href="/sign-up">Sign Up</Link>
              </>
            )}
          </div>
        </header>

        <div className="hero-layout">
          <div className="hero-copy">
            <span className="scene-kicker">Forecast Workspace</span>
            <h1>Stock Forecast Dashboard</h1>
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
              </div>

              <div className="hero-actions">
                <button className="ghost-button" disabled={isLoading || !authToken} type="submit">
                  {isLoading ? "Running forecasts" : "Run forecasts"}
                </button>
                <span className="hero-meta">
                  Run forecasts after signing in. GPT explanations are limited to 50 requests per
                  day for each account.
                </span>
                <span className="hero-meta">
                  Press Enter or comma to add tickers. Window {analysisWindowDays || "--"} days /
                  Horizon {forecastDays || "--"} days
                </span>
              </div>
            </form>

            {error ? <div className="system-warning">{error}</div> : null}
            {!currentUser ? (
              <div className="system-warning">
                <strong>Authentication required</strong>
                <span>Sign in or create an account to run forecasts and use GPT explanations.</span>
              </div>
            ) : null}

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

          <div className="overview-grid">
            <div className="overview-column">
              <StatusSummaryCard
                label="Requested Tickers"
                tone="warning"
                value={`${selectedTickers.length}`}
              />
              <StatusSummaryCard label="Failed Forecasts" tone="danger" value={`${failedCount}`} />
              <StatusSummaryCard
                label="Successful Forecasts"
                tone="success"
                value={`${successfulCount}`}
              />
            </div>

            <div className="overview-column">
              <SummaryCard label="Forecast Horizon" value={`${forecastDays || "--"} days`} />
              <SummaryCard label="Analysis Window" value={`${analysisWindowDays || "--"} days`} />
              <SummaryCard label="Models Used" value="Market Influence, ARIMA, XGBoost" />
            </div>
          </div>
        </div>
      </section>

      <section className="scene scene-results">
        <div className="scene-overlay scene-overlay-soft" />
        <div className="stocks-stack">
          {forecastCards.map((item) => (
            <StockForecastBoard
              currentUser={currentUser}
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
    </main>
  );
}

function StockForecastBoard({
  item,
  currentUser,
  onGenerateExplanation,
}: {
  item: ForecastCardState;
  currentUser: AuthUser | null;
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
          <span className="scene-kicker">{item.ticker}</span>
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

          <div className="summary-grid">
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
            <SummaryCard
              label="Selected Benchmark"
              value={summary?.selected_benchmark ?? "Waiting for forecast"}
            />
            <SummaryCard label="Confidence" value={formatScore(summary?.confidence_score)} />
            <SummaryCard
              label="Core Weight"
              value={formatWeight(findWeight(forecast, "market_influence"))}
            />
            <SummaryCard
              label="Warning Status"
              value={summary?.warning_status ?? "No warnings"}
            />
          </div>

          <ForecastChart forecast={forecast} />

          <div className="data-grid">
            <section className="data-column">
              <div className="scene-heading">
                <span className="scene-kicker">Model Components</span>
                <h2>Each model contributes to the final forecast output.</h2>
              </div>
              <div className="manifest-list">
                {forecast.ensemble_components.map((component) => (
                  <article className="manifest-row" key={component.model_id}>
                    <div>
                      <span className="manifest-label">{component.display_name}</span>
                      <p className="manifest-detail">
                        Status {component.status}
                        {component.detail ? ` / ${component.detail}` : ""}
                      </p>
                    </div>
                    <div className="manifest-values">
                      <span>{formatWeight(component.weight)}</span>
                      <span>{formatCurrency(component.terminal_price)}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="data-column">
              <div className="scene-heading">
                <span className="scene-kicker">Benchmark Selection</span>
                <h2>Benchmark candidates ranked by historical correlation.</h2>
              </div>
              <div className="rank-list">
                {forecast.benchmark_candidates.map((candidate, index) => (
                  <div className="rank-row" key={candidate.symbol}>
                    <span aria-hidden="true" className="rank-icon">
                      <span className="rank-icon-core" />
                    </span>
                    <div className="rank-content">
                      <span className="rank-name">{candidate.name}</span>
                      <span className="rank-symbol">{candidate.symbol}</span>
                      <div className="rank-metrics">
                        <span className="rank-position">No. {String(index + 1).padStart(2, "0")}</span>
                        <span className="rank-score">{candidate.correlation.toFixed(4)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="notes-grid">
            <section className="notes-block">
              <span className="scene-kicker">Diagnostics</span>
              <ul className="signal-list">
                <li>Analysis method: {diagnostics?.analysis_method ?? "Unavailable"}</li>
                <li>Alpha weight: {formatDecimal(summary?.alpha)}</li>
                <li>Fourier harmonics: {formatInteger(diagnostics?.fourier_harmonics_used)}</li>
                <li>ARIMA order: {diagnostics?.arima_order ?? "Unavailable"}</li>
                <li>ML samples: {formatInteger(diagnostics?.ml_training_samples)}</li>
                <li>Combination method: {diagnostics?.ensemble_method ?? "Unavailable"}</li>
              </ul>
            </section>

            <section className="notes-block">
              <span className="scene-kicker">Explanations</span>
              {currentUser ? (
                <div className="explanation-shell">
                  <p className="notes-copy">
                    Generate a grounded GPT summary based only on the structured forecast payload.
                  </p>
                  <div className="explanation-actions">
                    <button
                      className="ghost-button"
                      disabled={item.isExplanationLoading}
                      onClick={() => onGenerateExplanation(item.ticker)}
                      type="button"
                    >
                      {item.isExplanationLoading ? "Generating explanation" : "Generate Explanation"}
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
                        <strong>Plain-language summary</strong>
                        <p>{item.explanation.plain_language_explanation}</p>
                      </article>
                      <article className="explanation-section">
                        <strong>Reliability</strong>
                        <p>{item.explanation.reliability_summary}</p>
                      </article>
                      <article className="explanation-section">
                        <strong>Limitations</strong>
                        <p>{item.explanation.limitations_summary}</p>
                      </article>
                      <article className="explanation-section">
                        <strong>Disclaimer</strong>
                        <p>{item.explanation.disclaimer}</p>
                      </article>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="notes-copy">
                  Sign in with an approved account to generate GPT-backed explanations for this
                  forecast.
                </p>
              )}
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

function StatusSummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "warning" | "success" | "danger";
}) {
  return (
    <div className={`summary-card summary-card-status summary-card-${tone}`}>
      <span className="summary-label summary-label-status">
        <span aria-hidden="true" className="summary-status-dot" />
        <span>{label}</span>
      </span>
      <span className="summary-value summary-value-status">{value}</span>
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

function parsePositiveInteger(value: string): number | null {
  const parsed = Number.parseInt(value, 10);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
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

function formatInteger(value: number | null | undefined): string {
  if (value == null) {
    return "Unavailable";
  }

  return `${value}`;
}
