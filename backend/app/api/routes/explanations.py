from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.auth import get_current_approved_user
from app.models.schemas import ExplanationRequest, ExplanationResponse
from app.services.auth import AuthUser, QueryLimitExceededError, auth_service
from app.services.explanations import ForecastExplanationService


router = APIRouter(tags=["explanations"])
forecast_explanation_service = ForecastExplanationService()


@router.post("/explanations", response_model=ExplanationResponse)
def generate_explanation(
    payload: ExplanationRequest,
    current_user: AuthUser = Depends(get_current_approved_user),
) -> ExplanationResponse:
    try:
        auth_service.consume_daily_query(user_id=current_user.id)
        return forecast_explanation_service.explain(payload.forecast)
    except QueryLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate the explanation layer response.",
        ) from exc
