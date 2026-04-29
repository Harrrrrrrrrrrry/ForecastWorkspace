# Market Influence Model Workspace

Market Influence Model Platform is a full-stack academic stock forecasting system. It combines quantitative market analysis with a lightweight AI explanation layer, while keeping the forecast itself model-driven rather than LLM-generated.

## What It Does

- retrieves historical stock data from Yahoo Finance
- selects benchmark indices through correlation analysis
- generates forecasts with Market Influence, ARIMA, and XGBoost components
- blends model outputs into a final forecast with reliability checks
- provides open, plain-language explanations from the structured forecast payload

## Stack

- Backend: FastAPI, NumPy, pandas, statsmodels, scikit-learn, XGBoost
- Frontend: Next.js, React, TypeScript
- Data and AI: yfinance, OpenAI API

## Notes

This project is designed as an educational decision-support tool, not financial advice.

## Website link
https://forecastworkspace.vercel.app