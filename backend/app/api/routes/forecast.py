import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ForecastRequest, ForecastResponse
from app.services.market_influence import MarketInfluenceModelService


router = APIRouter(tags=["forecast"])
market_influence_service = MarketInfluenceModelService()
logger = logging.getLogger(__name__)


@router.post("/forecast", response_model=ForecastResponse)
def generate_forecast(
    payload: ForecastRequest,
) -> ForecastResponse:
    try:
        return market_influence_service.run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected forecast generation failure")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate the Market Influence Model forecast: {exc}",
        ) from exc
