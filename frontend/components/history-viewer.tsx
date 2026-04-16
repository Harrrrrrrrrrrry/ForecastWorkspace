"use client";

import { FormEvent, useState } from "react";

import { fetchStockHistory, StockHistoryResponse } from "@/lib/api";

const DEFAULT_TICKER = "AAPL";
const DEFAULT_LOOKBACK_DAYS = 180;

export function HistoryViewer() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [history, setHistory] = useState<StockHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      setError("Please enter a stock ticker.");
      setHistory(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchStockHistory(normalizedTicker, DEFAULT_LOOKBACK_DAYS);
      setHistory(response);
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Failed to load stock history.";
      setError(message);
      setHistory(null);
    } finally {
      setIsLoading(false);
    }
  }

  const latestPoint = history?.points.at(-1) ?? null;

  return (
    <div className="history-layout">
      <div className="panel input-panel">
        <div className="panel-inner">
          <form className="ticker-form" onSubmit={handleSubmit}>
            <div>
              <h2>Historical Data Lookup</h2>
              <p>
                Phase 2 fetches daily close prices from Yahoo Finance through the FastAPI backend.
                The quantitative forecast model is intentionally not implemented here yet.
              </p>
            </div>

            <div className="ticker-row">
              <input
                aria-label="Stock ticker"
                name="ticker"
                onChange={(event) => setTicker(event.target.value)}
                placeholder="Enter a ticker like AAPL"
                value={ticker}
              />
              <button disabled={isLoading} type="submit">
                {isLoading ? "Loading..." : "Load History"}
              </button>
            </div>
          </form>

          <div className="pill-row">
            <div className="pill">
              <span className="pill-label">Source</span>
              <span className="pill-value">{history?.source ?? "yfinance"}</span>
            </div>
            <div className="pill">
              <span className="pill-label">Lookback Window</span>
              <span className="pill-value">
                {history?.lookback_days ?? DEFAULT_LOOKBACK_DAYS} days
              </span>
            </div>
            <div className="pill">
              <span className="pill-label">Records Returned</span>
              <span className="pill-value">{history?.points.length ?? 0}</span>
            </div>
            <div className="pill">
              <span className="pill-label">Latest Close</span>
              <span className="pill-value">
                {latestPoint ? `${latestPoint.close.toFixed(2)} USD` : "--"}
              </span>
            </div>
          </div>

          {error ? <div className="status-note">{error}</div> : null}
        </div>
      </div>

      <div className="panel chart-panel">
        <div className="panel-inner">
          <h2>Daily Close Prices</h2>
          <p>
            This phase returns the historical series that the Market Influence Model will use in
            later phases for correlation analysis and forecasting.
          </p>

          <div className="table-shell">
            {history ? (
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Close</th>
                  </tr>
                </thead>
                <tbody>
                  {history.points.map((point) => (
                    <tr key={point.date}>
                      <td>{point.date}</td>
                      <td>{point.close.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <strong>No data loaded yet</strong>
                <p>Submit a ticker to retrieve historical close prices from the backend.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel notes-panel">
        <div className="panel-inner">
          <h2>Phase 2 Scope</h2>
          <ul className="list">
            <li>Backend endpoint: `/api/v1/stocks/{ticker}/history`.</li>
            <li>Source data: Yahoo Finance through `yfinance`.</li>
            <li>Response format: structured JSON with dates and close prices.</li>
            <li>Forecasting, benchmark selection, and AI explanations remain deferred.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
