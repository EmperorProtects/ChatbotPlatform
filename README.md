# Chatbot Platform

Microservices-based chatbot platform with API gateway, AI/knowledge services, channel adapters, and admin/web frontends.

## Architecture

Core services:
- `api_gateway` (port `8000`)
- `auth_service` (`8001`)
- `bot_service` (`8002`)
- `admin_service` (`8003`)
- `analytics_service` (`8004`)
- `ai_service` (`8005`)
- `knowledge_service` (`8006`)

Channel adapters:
- `whatsapp_adapter` (`8080`)
- `instagram_adapter`
- `web_adapter` (`8007`)

Frontends:
- Admin panel (`3000`)
- Optional monitoring: Prometheus (`9090`) and Grafana (`3001`)

Infrastructure:
- PostgreSQL (main + user data)
- Redis
- RabbitMQ
- Ollama
- ChromaDB

## Repository Structure

- `services/` — backend microservices and adapters
- `frontend/` — admin panel and embeddable web widget
- `scripts/` — DB initialization SQL
- `tests/` and root `test_*.py` — service/integration test runners
- `docker-compose.yml` — full local stack definition

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend local development)

## Quick Start (Docker)

1. Clone the repository.
2. (Optional) Create a `.env` file in the project root for secrets/overrides used by `docker-compose.yml` (for example `JWT_SECRET`, `OPENAI_KEY`, channel tokens).
3. Start the platform:

```bash
docker compose up --build
```

4. Open:
   - API Gateway: `http://localhost:8000`
   - Admin Panel: `http://localhost:3000`

To start monitoring components as well:

```bash
docker compose --profile monitoring up --build
```

## Running Tests

Run the master test runner:

```bash
python3 run_all_tests.py
```

Useful options:

```bash
python3 run_all_tests.py --quick
python3 run_all_tests.py --service knowledge
python3 run_all_tests.py --integration
python3 run_all_tests.py --report
```

> Note: quick health checks require Python dependency `httpx` to be installed in your active environment.
## Frontend Development

Admin panel:

```bash
cd frontend/admin-panel
npm install
npm run dev
```

Web widget:

```bash
cd frontend/web-widget
npm install
npm run dev
```
