from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import yfinance as yf

from app.models.schemas import StockHistoryPoint


class HistoricalDataProvider:
    """Retrieve historical daily close prices from Yahoo Finance."""

    def fetch_close_series(self, ticker: str, lookback_days: int) -> pd.Series:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("Ticker must not be empty.")

        end_date = datetime.now(UTC)
        # Add a small calendar-day buffer so weekends and market holidays do not reduce
        # the final trading-day window after we trim to the requested lookback length.
        start_date = end_date - timedelta(days=lookback_days + 15)

        history = yf.download(
            normalized_ticker,
            start=start_date.date().isoformat(),
            end=(end_date + timedelta(days=1)).date().isoformat(),
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        if history.empty:
            raise LookupError(f"No historical price data found for ticker '{normalized_ticker}'.")

        close_series = history["Close"]
        if hasattr(close_series, "columns"):
            close_series = close_series.iloc[:, 0]

        close_series = close_series.dropna().tail(lookback_days)
        close_series.index = pd.to_datetime(close_series.index)

        if close_series.empty:
            raise LookupError(f"No closing price data found for ticker '{normalized_ticker}'.")

        return close_series.astype(float)

    def fetch_price_history(self, ticker: str, lookback_days: int) -> list[StockHistoryPoint]:
        close_series = self.fetch_close_series(ticker=ticker, lookback_days=lookback_days)

        points = [
            StockHistoryPoint(
                date=index.strftime("%Y-%m-%d"),
                close=round(float(close_price), 4),
            )
            for index, close_price in close_series.items()
        ]

        return points
