from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd
import yfinance as yf

from app.models.schemas import StockHistoryPoint


class HistoricalDataProvider:
    """Retrieve historical daily close prices from Yahoo Finance."""

    def fetch_close_series(
        self,
        ticker: str,
        lookback_days: int,
        end_date: str | None = None,
    ) -> pd.Series:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("Ticker must not be empty.")

        requested_end_date = date.fromisoformat(end_date) if end_date else datetime.now(UTC).date()
        # Add a small calendar-day buffer so weekends and market holidays do not reduce
        # the final trading-day window after we trim to the requested lookback length.
        start_date = requested_end_date - timedelta(days=lookback_days + 15)

        history = yf.download(
            normalized_ticker,
            start=start_date.isoformat(),
            end=(requested_end_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        if history.empty:
            raise LookupError(f"No historical price data found for ticker '{normalized_ticker}'.")

        close_series = history["Close"]
        if hasattr(close_series, "columns"):
            close_series = close_series.iloc[:, 0]

        close_series = close_series.dropna()
        close_series.index = pd.to_datetime(close_series.index)
        close_series = close_series[close_series.index.date <= requested_end_date]
        close_series = close_series.tail(lookback_days)

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
