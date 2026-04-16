# Architecture Notes

## Goal

Build a web-based forecasting platform around the Market Influence Model while preserving the mathematical core as the authoritative source of predictions.

## Component Boundaries

### Frontend

- Collects user ticker input
- Displays charts, metrics, warnings, and explanation text
- Does not perform forecasting logic

### Backend

- Fetches historical data
- Runs the Market Influence Model
- Computes reliability signals
- Produces structured responses for both charts and explanations

### LLM Layer

- Receives only structured outputs from the backend
- Produces plain-language explanations, limitations, and confidence framing
- Never replaces forecasting logic

## Planned API Surface

- `GET /api/v1/health`
- `POST /api/v1/forecast`
- `POST /api/v1/explanations` in Phase 6

## Planned Forecast Response Shape

- Requested ticker and horizon
- Historical series
- Selected benchmark index
- Analysis window boundaries
- Fourier forecast series
- Index-based forecast series
- Final combined forecast series
- Alpha and correlation metadata
- Confidence score and warnings

