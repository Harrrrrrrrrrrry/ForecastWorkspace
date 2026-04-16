from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, explanations, forecast, health, stocks
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the Market Influence Model stock forecasting platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(stocks.router, prefix=settings.api_v1_prefix)
app.include_router(forecast.router, prefix=settings.api_v1_prefix)
app.include_router(explanations.router, prefix=settings.api_v1_prefix)
