from __future__ import annotations

from app.models.schemas import StockHistoryPoint, StockHistoryResponse
from app.services.data_provider import HistoricalDataProvider


class StockHistoryService:
    """Fetch historical daily close prices from Yahoo Finance."""

    def __init__(self, data_provider: HistoricalDataProvider | None = None) -> None:
        self.data_provider = data_provider or HistoricalDataProvider()

    def get_history(self, ticker: str, lookback_days: int = 180) -> StockHistoryResponse:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("Ticker must not be empty.")

        points: list[StockHistoryPoint] = self.data_provider.fetch_price_history(
            ticker=normalized_ticker,
            lookback_days=lookback_days,
        )

        return StockHistoryResponse(
            ticker=normalized_ticker,
            lookback_days=lookback_days,
            points=points,
        )
