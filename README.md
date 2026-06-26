# E-Commerce AI Studio

AI-powered image and video generation agent for e-commerce platforms (domestic + cross-border).

## Architecture

```
User (Web UI / API Client)
    │
FastAPI App (Auth + Tenancy + Projects + Assets)
    │
Agent Engine  ──  Model Gateway  ──  Task Queue (Celery)
    │                │                   │
    └────────────────┴───────────────────┘
                     │
    ┌────────────────┼────────────────────┐
    ▼                ▼                    ▼
  DALL·E          Flux/SD            可灵/Runway
  (Image)         (Image)            (Video)
                     │
         PostgreSQL + Redis + MinIO/S3
```

## Quick Start

### 1. Prerequisites
- Docker Desktop
- Python 3.12+
- Node.js 20+

### 2. Start Infrastructure
```bash
docker-compose up -d
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp ../.env.example .env  # Edit with your API keys

# Database migrations
alembic upgrade head

# Run API server
uvicorn app.main:app --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Worker Setup
```bash
cd backend
celery -A workers.celery_app worker --loglevel=info
```

Visit http://localhost:5173 to use the app.

## Configuration

All settings are managed via environment variables (`.env` file):

| Variable | Description |
|----------|-------------|
| `LLM_API_BASE` | LLM aggregation platform URL (Tokenpony/OpenRouter/etc.) |
| `LLM_API_KEY` | API key for LLM platform |
| `LLM_MODEL` | Default LLM model name |
| `FLUX_API_KEY` | Flux image generation API key |
| `OPENAI_API_KEY` | OpenAI API key (for DALL·E) |

See `.env.example` for the full list.

## API Endpoints

```
POST   /api/v1/auth/login              # Login
POST   /api/v1/auth/register           # Register
POST   /api/v1/generate/image          # Generate image
POST   /api/v1/generate/video          # Generate video
GET    /api/v1/generate/tasks/{id}     # Task status
GET    /api/v1/models                   # Available models
GET    /api/v1/assets                   # Asset library
```

## Development

```bash
# Run tests
cd backend
pytest

# Lint
ruff check .
```
