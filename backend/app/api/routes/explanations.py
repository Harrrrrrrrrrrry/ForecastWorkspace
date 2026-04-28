from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import ExplanationRequest, ExplanationResponse
from app.services.explanations import ForecastExplanationService
from app.services.rate_limit import ExplanationRateLimiter, RateLimitExceededError


router = APIRouter(tags=["explanations"])
forecast_explanation_service = ForecastExplanationService()
explanation_rate_limiter = ExplanationRateLimiter()


@router.post("/explanations", response_model=ExplanationResponse)
def generate_explanation(
    payload: ExplanationRequest,
    request: Request,
) -> ExplanationResponse:
    try:
        explanation_rate_limiter.check_and_consume(client_ip=_get_client_ip(request))
        return forecast_explanation_service.explain(payload.forecast)
    except RateLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate the explanation layer response.",
        ) from exc


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client:
        return request.client.host

    return "unknown"
