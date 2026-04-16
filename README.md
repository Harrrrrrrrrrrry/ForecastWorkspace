# Market Influence Model Platform

This repository contains a full-stack implementation of the **Market Influence Model**, built as an academic software system rather than a one-off demo.

The forecasting engine remains **model-driven**:

- Historical price data comes from Yahoo Finance via `yfinance`
- Benchmark selection is based on correlation analysis
- Forecasting combines a Fourier-based stock forecast with an index-based forecast
- The LLM layer is reserved for explanation and usability only

## Phase Plan

### Phase 1

- Define architecture
- Create backend and frontend skeletons
- Add environment variable support
- Add README and initial test scaffolding

### Phase 2

- Implement Yahoo Finance historical data retrieval
- Expose working stock history API endpoints
- Add a minimal frontend page for ticker-based history lookup

### Phase 3

- Implement correlation analysis
- Add benchmark index catalog and best-match selection
- Implement Fourier forecast
- Implement index-based forecast
- Implement combined final prediction
- Return structured model output

### Phase 4

- Wire frontend to backend
- Add interactive charts
- Add result cards, loading states, and error handling

### Phase 5

- Add outlier detection
- Add confidence scoring
- Add warning and fallback behavior

### Phase 6

- Add LLM explanation endpoint
- Ground prompts strictly on structured model outputs
- Add educational disclaimer and limitations panel

## Proposed Architecture

### Repository layout

```text
.
|-- backend/
|   |-- app/
|   |   |-- api/routes/         # FastAPI route modules
|   |   |-- core/               # Settings and app-wide config
|   |   |-- models/             # Pydantic request/response schemas
|   |   `-- services/           # Business logic and data/model services
|   |-- tests/
|   |-- .env.example
|   `-- pyproject.toml
|-- frontend/
|   |-- app/                    # Next.js App Router
|   |-- components/             # UI building blocks
|   |-- lib/                    # API client and helpers
|   |-- public/
|   |-- .env.example
|   `-- package.json
|-- docs/
|   `-- architecture.md
`-- README.md
```

### Backend responsibilities

- `app/services/data_provider.py`: fetch and normalize historical price data
- `app/services/market_influence.py`: implement the Market Influence Model
- `app/services/stocks.py`: orchestrate stock history retrieval responses
- `app/models/schemas.py`: stable API contracts between frontend and backend
- `app/api/routes/forecast.py`: endpoint orchestration only, not business logic
- `app/api/routes/stocks.py`: stock data retrieval endpoints

### Frontend responsibilities

- `app/page.tsx`: main dashboard shell
- `components/`: ticker form, summary cards, chart placeholders, explanation panel
- `lib/api.ts`: typed requests to the FastAPI backend

### Design decisions

- Keep quantitative logic in Python for numerical clarity and maintainability
- Keep the frontend focused on input, visualization, and interpretation
- Use versioned backend routes from the start: `/api/v1/...`
- Add reliability hooks early in the response schema so Phase 5 fits cleanly
- Treat AI explanation as a secondary service fed only structured outputs

## Local Setup

### Backend

1. Create a virtual environment
2. Install dependencies from `backend/pyproject.toml`
3. Copy `backend/.env.example` to `backend/.env`
4. Set `OWNER_EMAIL` and `OWNER_PASSWORD` in `backend/.env`
5. Run:

```bash
uvicorn app.main:app --reload --app-dir backend
```

### Frontend

1. Install dependencies in `frontend/`
2. Copy `frontend/.env.example` to `frontend/.env.local`
3. Run:

```bash
npm run dev --prefix frontend
```

## Environment Variables

### Backend

- `APP_NAME`: API display name
- `APP_ENV`: environment name
- `API_V1_PREFIX`: route prefix
- `CORS_ORIGINS`: comma-separated frontend origins
- `AUTH_DB_PATH`: SQLite file used for local auth state
- `AUTH_TOKEN_TTL_DAYS`: bearer token lifetime in days
- `OWNER_EMAIL`: bootstrap email for the initial owner account
- `OWNER_PASSWORD`: bootstrap password for the initial owner account
- `OWNER_FULL_NAME`: optional display name for the owner account
- `OPENAI_API_KEY`: OpenAI API key for the explanation endpoint
- `OPENAI_MODEL`: model used by the explanation endpoint

### Frontend

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI base URL

## Auth Workflow

- The backend bootstraps one approved `owner` account from `OWNER_EMAIL` and `OWNER_PASSWORD`.
- New users who sign up through the frontend are created as `pending` members.
- Pending users cannot sign in until an `owner` or `admin` approves them.
- GPT-backed explanation access is restricted to approved users.
- Admin review uses authenticated backend routes:
  - `GET /api/v1/auth/admin/users?status=pending`
  - `POST /api/v1/auth/admin/approve`

## Status

The repository now includes:

- A working FastAPI health endpoint
- A Phase 2 stock history endpoint at `/api/v1/stocks/{ticker}/history`
- A simple frontend page that requests and displays returned daily close data
- A Phase 3 forecast endpoint at `/api/v1/forecast`
- Modular backend services for benchmark analysis, Fourier forecasting, and final forecast blending
- Reliability-aware backend logic for confidence scoring, outlier detection, warning banners, and conservative fallback handling
- An explanation endpoint at `/api/v1/explanations` that uses the OpenAI API only as a text explanation layer over structured forecast output

Interactive frontend forecast visualizations remain pending later phases.
