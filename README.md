# Market Influence Model Workspace

Market Influence Model Platform is a full-stack academic stock forecasting system. It combines quantitative market analysis with a lightweight AI explanation layer, while keeping the forecast itself model-driven rather than LLM-generated.

## What It Does

- retrieves historical stock data from Yahoo Finance
- selects benchmark indices through correlation analysis
- generates forecasts with Market Influence, ARIMA, and XGBoost components
- blends model outputs into a final forecast with reliability checks
- provides authenticated, plain-language explanations for approved users

## Stack

- Backend: FastAPI, NumPy, pandas, statsmodels, scikit-learn, XGBoost
- Frontend: Next.js, React, TypeScript
- Data and AI: yfinance, OpenAI API

## Repository

- `backend/`: API routes, forecasting services, auth, and tests
- `frontend/`: dashboard, charts, auth pages, and API client
- `docs/architecture.md`: architecture notes

## Notes

This project is designed as an educational decision-support tool, not financial advice.
