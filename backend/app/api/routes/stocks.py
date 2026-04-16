from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import StockHistoryResponse
from app.services.stocks import StockHistoryService


router = APIRouter(prefix="/stocks", tags=["stocks"])

stock_history_service = StockHistoryService()


@router.get("/{ticker}/history", response_model=StockHistoryResponse)
def get_stock_history(
    ticker: str,
    lookback_days: int = Query(default=180, ge=30, le=730),
) -> StockHistoryResponse:
    try:
        return stock_history_service.get_history(ticker=ticker, lookback_days=lookback_days)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve data from Yahoo Finance.",
        ) from exc
