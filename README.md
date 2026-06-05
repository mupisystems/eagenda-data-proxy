# eagendas Data Proxy

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red)](https://github.com/sponsors/mupisystems)

On-premise PII proxy for eagendas API v3. Keeps personal data (name, email, phone, CPF) on the client's servers while using eagendas cloud for scheduling.

## Architecture

```
Client Systems → Data Proxy (on-premise) → eagendas Cloud
                  ├─ PII Store (local DB)
                  ├─ Notifications (SMTP)
                  └─ Admin Panel (/admin)
```

- **Intercept**: PII is stripped from outbound requests and stored locally
- **Pseudonymize**: Names become `Citizen-{external_id}` in the cloud (configurable prefix)
- **Enrich**: Cloud responses are merged with local PII before returning to client
- **Notify**: Email/SMS sent using real contact data from local store

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your credentials

# 2. Start all services
docker compose up -d

# 3. Run migrations
docker compose exec proxy alembic upgrade head

# 4. Create admin user and API token
docker compose exec proxy python -m app.auth.create_token --label "My System"

# 5. Test
curl -H "Authorization: Bearer <token>" http://localhost:8000/health/
```

## API

Same interface as eagendas API v3. Client systems call the proxy instead of eagendas directly:

```
# Instead of:
POST https://eagendas.com/api/v3/people/

# Call:
POST https://proxy.local:8000/api/v3/people/
```

## Endpoints

| Method | Path | PII Handling |
|--------|------|-------------|
| GET/POST/PUT/PATCH | `/api/v3/people/` | Intercept + Enrich |
| GET/POST/PATCH/DELETE | `/api/v3/appointments/` | Intercept attendees + Enrich |
| PATCH | `/api/v3/appointments/{key}/reschedule/` | Enrich response |
| GET | `/api/v3/calendars/` | Pass-through |
| GET | `/api/v3/calendars/{key}/forms/` | Pass-through |
| GET | `/api/v3/days/` | Pass-through |
| GET | `/api/v3/available-date-times/` | Pass-through |
| GET | `/api/v3/services/` | Pass-through |
| POST | `/webhooks/receive/` | Enrich + Relay |
| GET | `/health/` | Health check |
| GET | `/admin/` | Admin panel |

## Configuration

See `data_proxy_config.yml` for all settings. Environment variables can be referenced with `${VAR_NAME}`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Datacenter Regions

Configure which eagendas datacenter to use:

| Region | Base URL | Description |
|--------|----------|-------------|
| `BR` | `https://eagenda.com.br/api/v3` | Brazil (default) |
| `US` | `https://eagendas.com/api/v3` | United States |
| `HOMOLOG` | `https://homolog.eagendas.com/api/v3` | Staging / QA |

Set in `.env`:
```bash
EAGENDAS_REGION=BR
```

Or override with a custom URL:
```bash
EAGENDAS_API_URL=https://custom.eagendas.example.com/api/v3
```

## Tech Stack

- FastAPI + uvicorn
- SQLAlchemy 2.0 (async) + PostgreSQL
- Celery + Redis
- SQLAdmin
- Docker Compose

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).

### Commercial Use

If you need a commercial license without AGPL obligations, or want priority support and managed hosting, contact us or become a [sponsor](https://github.com/sponsors/mupisystems).

| Tier | Includes |
|------|----------|
| Community | AGPL-3.0, community support |
| Sponsor | Priority issues, private support channel |
| Enterprise | Commercial license, SLA, managed deployment |
