# GridMind AI

GridMind AI is a web-based energy intelligence platform for exploring electricity-consumption data, training forecasting models, detecting unusual usage, and planning flexible loads against electricity tariffs. It combines a React dashboard with a FastAPI backend and a local SQLite-based data store.

> **Project status:** Core frontend and backend workflows are implemented. Generated and uploaded datasets, model training, forecasts, anomaly detection, optimization, and experiment history are available through the application and REST API. Model quality depends on the dataset and should be validated for each real deployment.

## Contents

- [Project at a glance](#project-at-a-glance)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture and data flow](#architecture-and-data-flow)
- [Requirements](#requirements)
- [Run locally on Windows](#run-locally-on-windows)
- [Run locally on macOS or Linux](#run-locally-on-macos-or-linux)
- [Run with Docker Compose](#run-with-docker-compose)
- [Configuration and API key](#configuration-and-api-key)
- [First-use workflow](#first-use-workflow)
- [Dataset format and synthetic data](#dataset-format-and-synthetic-data)
- [Forecasting models and evaluation](#forecasting-models-and-evaluation)
- [REST API reference](#rest-api-reference)
- [Testing and quality checks](#testing-and-quality-checks)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Security and production notes](#security-and-production-notes)
- [AI presentation prompt](#ai-presentation-prompt)

## Project at a glance

| Area | Description |
|---|---|
| Purpose | Turn time-stamped energy usage into forecasts, anomaly insights, and flexible-load schedules |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Recharts, and Lucide icons |
| Backend | Python 3.11+, FastAPI, Pydantic, and Uvicorn |
| Data | Pandas and NumPy; SQLite for application metadata and history |
| Machine learning | scikit-learn, XGBoost, and custom NumPy recurrent forecasters |
| Optimization | SciPy-based optimization with service-level solver/fallback logic |
| Default local URLs | Frontend `http://localhost:5173`; API `http://localhost:8000` |
| API documentation | Swagger UI at `http://localhost:8000/docs`; ReDoc at `http://localhost:8000/redoc` |

## Features

### Dashboard

The dashboard provides a high-level view of the selected energy dataset, recent consumption history, a forecast summary, detected anomalies, and optimization savings when those results are available.

### Data Explorer

- Upload CSV data.
- Generate synthetic hourly or 15-minute energy data.
- Browse datasets and inspect summary statistics, previews, and quality information.
- Review row counts, columns, date range, missing values, and duplicate timestamps.
- Delete datasets that are no longer needed.

### Forecast Lab

- Train a forecasting model on a selected dataset.
- Review model status, training duration, evaluation metrics, and feature importance where available.
- Generate forecasts for a configurable horizon.
- View forecast values and uncertainty bounds when returned by the backend.

### Anomaly Monitor

Available detection methods are:

- `statistical` — statistical/rolling-window analysis.
- `isolation_forest` — unsupervised outlier detection.
- `residual` — deviations from a forecasting model.

Anomaly results include observed and expected values, deviation, severity, and an explanatory message where the detector produces one.

### Optimization Studio

- Describe flexible electrical loads by power, duration, operating window, priority, and whether the load must run continuously.
- Supply a tariff schedule and a planning horizon.
- Balance cost and peak-demand objectives using configurable weights.
- Compare optimization scenarios and review schedules, cost changes, peak changes, and reported constraint violations.

### Experiments

Model training and evaluation results are recorded for later review. The experiments API can list and export records in JSON or CSV format.

### Methodology

The application includes an in-product methodology page describing the forecasting, anomaly detection, and scheduling concepts used by GridMind AI.

## Technology stack

### Frontend

- React 19 and TypeScript
- Vite 8
- React Router
- Tailwind CSS
- Recharts
- Lucide React
- Vitest and Oxlint development tooling

### Backend

- Python 3.11
- FastAPI and Uvicorn
- Pydantic Settings
- Pandas and NumPy
- scikit-learn and XGBoost
- SciPy and Joblib
- SQLite
- Pytest and HTTPX for tests

## Architecture and data flow

```text
Browser
  |
  | React SPA requests (JSON / CSV upload)
  | X-API-Key header for protected routes
  v
FastAPI backend :8000
  |-- Dataset service       -> CSV files + SQLite metadata
  |-- Forecasting service   -> trained model artifacts + metrics
  |-- Anomaly service       -> detection results
  |-- Optimization service -> schedules and comparisons
  |-- Experiment API       -> training history and exports
  v
SQLite database and backend data/model directories
```

The backend initializes its SQLite schema when the application starts. Uploaded and generated data is saved as CSV files; model artifacts are serialized under the configured models directory. The default directories are defined in `backend/app/core/config.py` and can be overridden with environment variables.

## Requirements

For local development:

- Python 3.11 or newer
- Node.js 20 or newer and npm
- Git (optional, for cloning/version control)

For containerized development:

- Docker Desktop or Docker Engine
- Docker Compose

The frontend and backend are separate processes during local development. Keep each running in its own terminal.

## Run locally on Windows

Open PowerShell in the project directory.

### 1. Start the backend

The project already has a backend virtual environment in `backend\venv`. Activate it:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
```

If you have not created the environment yet, create it and install the backend requirements:

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create or update `backend\.env` with local development settings:

```env
APP_NAME=GridMind AI
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000","http://localhost:4173","http://127.0.0.1:4173"]
DATABASE_URL=sqlite:///./gridmind.db
GRIDMIND_API_KEY=dev-secret-change-in-production
RANDOM_SEED=42
```

Start the API from the `backend` directory:

```powershell
python run.py
```

Alternatively, start Uvicorn directly:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the backend at `http://localhost:8000/api/health`. The root endpoint is `http://localhost:8000/`.

### 2. Start the frontend

Open a second PowerShell window:

```powershell
cd frontend
npm install
```

Create `frontend\.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=dev-secret-change-in-production
```

Start the Vite development server:

```powershell
npm run dev
```

Open `http://localhost:5173`.

> Vite reads `VITE_*` variables when it starts/builds. Restart the frontend after changing `frontend\.env`.

## Run locally on macOS or Linux

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend/.env` using the configuration example above, then start the API:

```bash
python run.py
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=dev-secret-change-in-production
```

Then start the UI:

```bash
npm run dev
```

## Run with Docker Compose

From the repository root:

```bash
docker compose up --build
```

The Compose configuration starts the backend and frontend, waits for the backend health check before starting the frontend, and uses named volumes for backend data, model artifacts, and experiment files.

Default addresses:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

To use a different local key, set `GRIDMIND_API_KEY` in the shell or in a Compose `.env` file at the repository root before building/starting. The same value is passed to the backend and used as the frontend build argument.

```powershell
# PowerShell example
$env:GRIDMIND_API_KEY = "replace-with-a-local-development-value"
docker compose up --build
```

```bash
# macOS/Linux example
export GRIDMIND_API_KEY='replace-with-a-local-development-value'
docker compose up --build
```

Stop the containers with `Ctrl+C`, or run `docker compose down` in another terminal. Named volumes are retained by `docker compose down`; do not use volume-removal options unless you intend to delete the stored application data.

## Configuration and API key

GridMind AI does **not** require an external AI provider key for its local forecasting, anomaly detection, or optimization workflows.

The app does use a local application API key to authenticate protected backend routes:

| Setting | Used by | Purpose |
|---|---|---|
| `GRIDMIND_API_KEY` | Backend | Expected key for protected API endpoints |
| `VITE_API_KEY` | Frontend | Value sent in the `X-API-Key` request header |
| `VITE_API_URL` | Frontend | Base URL for the backend, defaulting to `http://localhost:8000` |

For local use, the backend `GRIDMIND_API_KEY` and frontend `VITE_API_KEY` must match. The repository's current development value is `dev-secret-change-in-production`; replace it for any shared or deployed environment. Do not place a production secret in a browser-based frontend: Vite variables are compiled into the client and can be inspected by users. Production deployments should use a suitable authentication architecture and keep server-side secrets server-side.

`/` and `/api/health` are public health/info routes. The dataset, model, forecast, anomaly, optimization, and experiment routers require the `X-API-Key` header.

Other configurable backend settings include:

| Variable | Default / notes |
|---|---|
| `APP_NAME` | `GridMind AI` |
| `DEBUG` | `true` in settings; set deliberately for the environment |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |
| `CORS_ORIGINS` | List of allowed frontend origins; configure for your actual UI URL |
| `DATABASE_URL` | `sqlite:///./gridmind.db` |
| `DATA_DIR` | Defaults to `backend/data` |
| `MODELS_DIR` | Defaults to `backend/models` |
| `EXPERIMENTS_DIR` | Defaults to `backend/experiments` |
| `MAX_UPLOAD_SIZE` | `10485760` bytes (10 MiB) |
| `RANDOM_SEED` | `42` |

The SQLite URL is relative to the backend process's working directory. Start the backend from the `backend` folder to keep the database in the expected location.

## First-use workflow

1. Start the backend and frontend using one of the local or Docker options above.
2. Open the frontend and go to **Data Explorer**.
3. Click **Generate Synthetic** to create a trial dataset, or upload a CSV.
4. Select the generated/uploaded dataset and review its overview, preview, and quality details.
5. Open **Forecast Lab**, select a dataset and model type, and train a model.
6. Review validation/test metrics and use the trained model to produce a forecast.
7. Optionally inspect **Anomaly Monitor** for unusual observations.
8. In **Optimization Studio**, define flexible loads and tariff periods, then run an optimization or compare scenarios.
9. Review saved training/evaluation information in **Experiments**.

For a first model-training trial, use at least a few days of hourly data; the built-in 30-day hourly synthetic dataset is a good starting point. If a model reports a feature or timestamp error, confirm that the input CSV contains a parseable timestamp column and a numeric consumption column.

## Dataset format and synthetic data

### CSV upload

The forecasting pipeline expects the normalized fields:

```csv
timestamp,consumption_kwh
2026-01-01 00:00:00,35.8
2026-01-01 01:00:00,34.2
2026-01-01 02:00:00,32.9
```

During upload, the backend looks for a timestamp/date/time-like column and a numeric energy/power/consumption/demand/load-like column. If it cannot identify a timestamp column, it creates an hourly sequence starting at 2023-01-01. If it cannot identify a named consumption column, it can use the last numeric column. The uploaded series is normalized to hourly observations by resampling and filling gaps. For predictable results, provide an explicit timestamp column and one numeric consumption column.

Timestamps should be parseable by Pandas. Consumption values should be numeric and use consistent units. The app labels common values in kWh/kW for display, but it cannot infer or convert arbitrary physical units.

### Synthetic data generation

Synthetic data is generated locally by the backend; no external AI service is called. It includes an hourly or 15-minute time series, a daily demand pattern, weekday/weekend variation, a seasonal component, a trend, random noise, and optional spikes for anomaly trials.

Supported frequencies are `h` and `15min`. The UI's current quick-generate action creates a 30-day hourly dataset with anomalies enabled. For initial model training, turning anomalies off can make baseline metrics easier to interpret.

## Forecasting models and evaluation

The backend model registry currently includes:

| Model type | General approach |
|---|---|
| `persistence` | Uses the latest observed value as a baseline |
| `seasonal_naive` | Repeats a recent seasonal pattern |
| `linear_regression` | Linear regression baseline |
| `ridge` | L2-regularized linear regression |
| `lasso` | L1-regularized linear regression |
| `random_forest` | Tree ensemble |
| `gradient_boosting` | Gradient-boosted tree ensemble |
| `xgboost` | XGBoost regression |
| `lstm` | Self-contained NumPy recurrent model |
| `gru` | Self-contained NumPy recurrent model |

Forecasting features include hour of day, day of week, weekend indicator, month, lagged demand, rolling statistics, and trend information. The training pipeline parses timestamp strings, sorts observations chronologically, and uses chronological train/validation/test splits rather than randomly shuffling a time series.

The API reports common regression metrics, including MAE, MSE, RMSE, R², and MAPE when it can be calculated. These metrics are dataset- and split-dependent; they do not guarantee future accuracy. Compare models on an untouched test period and validate performance against real operational data before using the forecasts for decisions.

Forecast requests accept horizons from 1 to 168 hours. Forecast results may include lower and upper bounds derived from validation residuals.

## REST API reference

Base URL: `http://localhost:8000`

Protected requests require:

```http
X-API-Key: <same value as GRIDMIND_API_KEY>
```

The interactive API schema is available at `/docs` and `/redoc`. For exact request/response models, use those live docs because the backend schema is authoritative.

### Health and information

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `GET` | `/` | No | API name and links |
| `GET` | `/api/health` | No | Health status and version |

### Datasets

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `GET` | `/api/datasets/` | Yes | List datasets |
| `POST` | `/api/datasets/upload` | Yes | Upload CSV as multipart form field `file` |
| `POST` | `/api/datasets/generate` | Yes | Generate synthetic data; query parameters `days`, `freq`, `anomalies` |
| `POST` | `/api/datasets/generate-synthetic` | Yes | Alias for synthetic generation |
| `GET` | `/api/datasets/{dataset_id}/summary` | Yes | Dataset totals, extrema, quality, and date range |
| `GET` | `/api/datasets/{dataset_id}/preview?limit=50` | Yes | Preview rows |
| `GET` | `/api/datasets/{dataset_id}/history?limit=168` | Yes | Recent time-series observations |
| `DELETE` | `/api/datasets/{dataset_id}` | Yes | Delete dataset record and its CSV |

Example synthetic-data request:

```bash
curl -X POST "http://localhost:8000/api/datasets/generate?days=30&freq=h&anomalies=false" \
  -H "X-API-Key: dev-secret-change-in-production"
```

PowerShell example:

```powershell
$headers = @{ "X-API-Key" = "dev-secret-change-in-production" }
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/datasets/generate?days=30&freq=h&anomalies=false" `
  -Method Post `
  -Headers $headers
```

### Models and forecasts

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `POST` | `/api/models/train` | Yes | Train a model from `dataset_id` and `model_type`; optional hyperparameters and split settings |
| `GET` | `/api/models/` | Yes | List trained models |
| `GET` | `/api/models/{model_id}` | Yes | Get model details |
| `GET` | `/api/models/{model_id}/metrics` | Yes | Get metrics and feature importance |
| `DELETE` | `/api/models/{model_id}` | Yes | Delete model record/artifact |
| `POST` | `/api/models/{model_id}/forecast?horizon_hours=24` | Yes | Generate forecast through the model route |
| `POST` | `/api/forecast/` | Yes | Generate forecast using JSON body with `model_id` and `horizon_hours` |
| `GET` | `/api/forecast/` | Yes | List forecasts |
| `GET` | `/api/forecast/{forecast_id}` | Yes | Retrieve a forecast |

Example training body:

```json
{
  "dataset_id": "YOUR_DATASET_ID",
  "model_type": "ridge",
  "hyperparameters": {},
  "train_split": 0.7,
  "val_split": 0.15
}
```

Supported model type strings are listed in [Forecasting models and evaluation](#forecasting-models-and-evaluation).

### Anomaly detection

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `POST` | `/api/anomalies/detect` | Yes | Detect anomalies with a dataset, method, sensitivity, and optional window size |
| `GET` | `/api/anomalies/` | Yes | List anomaly detection results |
| `GET` | `/api/anomalies/{anomaly_id}` | Yes | Retrieve a detection result |

Allowed detection methods are `statistical`, `isolation_forest`, and `residual`. The API schema constrains sensitivity to 1.0–5.0 and the optional window size to 1–168.

### Optimization

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `POST` | `/api/optimization/run` | Yes | Run flexible-load schedule optimization |
| `POST` | `/api/optimization/scenarios` | Yes | Compare optimization scenarios |
| `GET` | `/api/optimization/` | Yes | List optimization results |
| `GET` | `/api/optimization/{optimization_id}` | Yes | Retrieve an optimization result |

Optimization requests include `dataset_id`, at least one `flexible_load`, at least one `tariff_schedule` period, a horizon (1–168 hours), and cost/peak weights. A flexible load includes its name, positive power and duration, earliest start and latest end in `HH:MM` format, priority, and continuity requirement. Refer to `/docs` for the full JSON schema.

### Experiments

| Method | Endpoint | Auth | Purpose |
|---|---|---:|---|
| `GET` | `/api/experiments/` | Yes | List saved experiments/training results |
| `GET` | `/api/experiments/export?format=json` | Yes | Download JSON export |
| `GET` | `/api/experiments/export?format=csv` | Yes | Download CSV export |
| `GET` | `/api/experiments/{experiment_id}` | Yes | Retrieve one experiment |

## Testing and quality checks

### Backend tests

Run from the `backend` directory with the project environment activated:

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
pytest -v
```

```bash
# macOS/Linux
source venv/bin/activate
pytest -v
```

To run the focused timestamp/feature-engineering regression tests:

```bash
pytest -q tests/test_forecasting_features.py
```

### Frontend checks

Run from `frontend`:

```bash
npm run build
npm run lint
npm run test
```

Vitest is configured by the project package scripts. `npm run test:coverage` runs the configured coverage command. If a test runner is left in watch mode, use its run/CI mode as appropriate.

## Project layout

```text
GridMindAI/
|-- backend/
|   |-- app/
|   |   |-- api/          # FastAPI route modules
|   |   |-- core/         # Settings and API-key authentication
|   |   |-- persistence/  # SQLite connection and schema initialization
|   |   |-- schemas/      # Pydantic request/response types
|   |   `-- services/     # Data, forecasting, anomaly, optimization logic
|   |-- tests/            # Backend regression and API tests
|   |-- data/             # Uploaded/generated dataset CSVs
|   |-- models/           # Serialized model artifacts
|   |-- experiments/      # Experiment-related local files
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- src/
|   |   |-- components/   # Shared UI and layout
|   |   |-- pages/        # Dashboard and feature pages
|   |   |-- services/     # Backend API client
|   |   `-- tests/        # Frontend tests
|   `-- package.json
|-- docker-compose.yml
`-- README.md
```

## Troubleshooting

### `403 Forbidden` or `API key is missing`

1. Confirm `backend/.env` has `GRIDMIND_API_KEY`.
2. Confirm `frontend/.env` has the same value as `VITE_API_KEY`.
3. Restart both processes after editing environment files.
4. Check that the frontend is calling the expected backend URL in `VITE_API_URL`.
5. For direct API calls, add `X-API-Key` with the matching value.

The local key is an application API key, not an AI-service key.

### Synthetic generation fails

- Check the backend terminal for the API error body.
- Confirm the backend is reachable at the configured API URL.
- Use a positive `days` value and `freq=h` or `freq=15min`.
- Check that the backend data directory is writable and the SQLite database can be opened.

### Model training reports a missing timestamp/hour feature

- Use a dataset with a parseable timestamp column and numeric consumption values.
- The backend feature pipeline parses timestamp strings, but malformed or missing timestamps are discarded; a dataset with no remaining valid rows cannot train.
- For CSV uploads, use the canonical columns `timestamp` and `consumption_kwh` to avoid ambiguity.
- Try a multi-day hourly dataset such as the generated 30-day trial data.

### Frontend cannot connect to the backend

- Confirm the backend health URL returns JSON: `http://localhost:8000/api/health`.
- Ensure `VITE_API_URL` points to the backend host/port.
- Ensure the UI origin is included in backend `CORS_ORIGINS`.
- Restart Vite after changing `.env`.

### Port already in use

Change the port passed to Uvicorn or Vite and update `API_PORT`, `VITE_API_URL`, and `CORS_ORIGINS` consistently. The Docker Compose port mappings also need to match the desired host ports.

### Native NumPy/SciPy or memory errors on Windows

Machine-learning packages can depend on native numerical libraries and available system memory. Activate the project's existing virtual environment, avoid running multiple heavy training processes at once, and use a smaller dataset/model while diagnosing package installation or operating-system resource problems.

## Security and production notes

- The default API key is only for local development. Replace it before sharing the application.
- `VITE_API_KEY` becomes part of the client-side application bundle; it is not a secure place for a production secret.
- Configure a real authentication and authorization strategy before exposing the API to untrusted networks.
- Restrict `CORS_ORIGINS` to trusted application origins.
- Do not commit `.env` files, credentials, production data, model files, or database contents.
- Use HTTPS/TLS at the deployment edge and protect persistent volumes/backups.
- Review uploaded CSV size and content, retention requirements, and privacy obligations for real energy data.
- SQLite is convenient for local development and demonstrations. Evaluate a managed/server database, concurrent-write behavior, backups, monitoring, and operational recovery requirements before production.
- Do not treat model outputs as guaranteed measurements or control instructions. Validate models and optimization schedules with domain experts and operational constraints.

## AI presentation prompt

Copy the prompt below into an AI presentation tool such as PowerPoint Copilot, Gamma, Canva, or another slide-generation assistant. Replace bracketed details with your own information and add actual screenshots or measured results where indicated.

```text
Create a polished, professional 10–12 slide presentation introducing and demonstrating my college capstone project, “GridMind AI: Energy Intelligence Platform.”

PROJECT CONTEXT
GridMind AI is a full-stack web application for electricity-consumption data exploration, time-series forecasting, anomaly detection, and flexible-load schedule optimization. It has a React 19 + TypeScript + Vite frontend and a Python 3.11+ FastAPI backend. The backend uses Pandas and NumPy for data processing; SQLite for local application metadata; scikit-learn, XGBoost, and self-contained NumPy LSTM/GRU implementations for forecasting; and SciPy-based optimization with service-level fallback logic. Users can upload CSV data or generate synthetic energy data, train and evaluate forecasting models, inspect anomalies, define flexible loads and tariff periods, compare schedules, and review saved experiment results.

The application includes these screens: Dashboard, Data Explorer, Forecast Lab, Anomaly Monitor, Optimization Studio, Experiments, and Methodology. Protected backend routes use an X-API-Key header for local/demo authentication. There is no external AI-provider dependency for the app's local model-training workflow.

AUDIENCE AND PURPOSE
Present to [faculty / classmates / project evaluators / energy-domain stakeholders]. The goal is to explain the problem, show how the platform works, communicate the technical design clearly, and demonstrate its value without overstating experimental results. Use accessible language first, then explain relevant technical details. Add speaker notes with concise talking points and suggested narration for every slide.

DESIGN DIRECTION
- Use a modern energy-tech visual identity: deep navy or charcoal backgrounds, crisp white space, electric teal/green highlights, and restrained amber for warnings/anomalies.
- Use clear typography, high contrast, consistent alignment, and generous spacing.
- Prefer diagrams, annotated UI screenshots, time-series charts, model pipeline illustrations, and compact metrics over paragraphs.
- Keep each slide focused on one message. Use no more than 3–5 concise bullets on a slide.
- Use a consistent icon style for data, forecasting, anomalies, optimization, security, and deployment.
- Make charts legible with labeled axes, units, and a legend. Do not use invented chart data as if it came from a real evaluation.
- Leave clearly labeled placeholders for actual application screenshots, measured model scores, and project/team information where values have not been supplied.

SLIDE PLAN
1. Title: GridMind AI — Energy Intelligence Platform. Include subtitle, presenter [name], institution [institution], course/program [course], and date [date]. Use a refined energy-grid visual, not a generic stock-photo collage.
2. The problem: Explain why energy demand variability, peak loads, unexpected consumption, and time-of-use tariffs make planning difficult. State the project's motivation and identify the target users as [insert intended users; do not assume].
3. Project goals and scope: Summarize the core goals—understand consumption, forecast demand, flag unusual behavior, and explore better schedules. Distinguish what is implemented from future work.
4. Product walkthrough: Show the user journey: generate/upload a dataset → inspect data quality → train a model → forecast → detect anomalies → optimize flexible loads → review experiment history. Use a left-to-right workflow graphic and place [actual UI screenshot] as a placeholder.
5. System architecture: Diagram Browser (React/TypeScript) → FastAPI REST API → service modules (data, forecasting, anomalies, optimization, experiments) → SQLite plus dataset/model storage. Mark the X-API-Key boundary and distinguish public health endpoints from protected feature APIs. Do not imply cloud deployment if not actually configured.
6. Data and preparation: Explain accepted time-series data fields (`timestamp`, `consumption_kwh`), CSV upload, hourly resampling/cleanup, and locally generated hourly/15-minute synthetic trials. Explain that synthetic data is for testing, not evidence of real-world performance.
7. Forecasting approach: Show the pipeline (timestamp parsing → calendar/lag/rolling features → chronological train/validation/test split → model training → metrics → forecast). List the implemented model families: persistence, seasonal naive, linear regression, Ridge, Lasso, Random Forest, Gradient Boosting, XGBoost, NumPy LSTM, and NumPy GRU. Explain MAE, RMSE, R², and MAPE in simple terms. Do not fabricate model scores; add a placeholder [insert measured metrics from a real run].
8. Anomaly detection: Explain the three available methods—statistical, Isolation Forest, and forecast residuals. Show a simple illustrative timeline with a marked spike, explicitly labeling it as illustrative unless it comes from a real dataset.
9. Flexible-load optimization: Explain the inputs (load power/duration/windows/priority/continuity, tariff periods, horizon, cost-vs-peak weights) and outputs (baseline and optimized schedules, cost/peak comparisons, constraint notices). Avoid claiming guaranteed savings; use [insert measured result, if available].
10. Application experience and API: Use a concise dashboard screenshot or a visual map of the seven pages. Mention FastAPI/Swagger documentation and protected API routes only as implementation details; keep the slide readable.
11. Validation, limitations, and responsible use: State what has actually been tested: [insert current test/build results]. Explain limitations: results depend on data quality and quantity, synthetic results do not prove field performance, forecasts are uncertain, optimization requires valid operational constraints, local API-key authentication is not production-grade, and a production deployment needs security/monitoring/backup work.
12. Conclusion and next steps: Recap the value of an integrated workflow from consumption data to actionable planning. Suggest realistic future work such as external real-world dataset validation, richer weather/calendar features, model comparison and calibration, stronger authentication, database/deployment hardening, and user feedback. Finish with a concise thank-you / Q&A slide treatment.

CONTENT ACCURACY RULES
- Do not invent measured accuracy, savings, adoption, customer outcomes, or production deployment.
- Mark mock/synthetic chart values as illustrative.
- Separate implemented features from proposed future enhancements.
- If evidence is unavailable, use a visible placeholder such as [add measured test result] instead of making up a number.
- Keep terminology consistent: energy consumption, forecast horizon, anomaly, flexible load, tariff, baseline, and optimized schedule.
- Include a brief source/notes line on slides with external facts; use only reputable, verifiable sources and provide URLs in speaker notes. Do not add unsourced statistics.

OUTPUT
Generate an editable 16:9 slide deck with a cohesive visual system, speaker notes for each slide, and a final references/credits note if external sources are used. Include a short presenter script for the demo transition from the Data Explorer to Forecast Lab and Optimization Studio. Ensure all chart and screenshot placeholders are visibly identified so I can replace them with authentic project evidence.
```
