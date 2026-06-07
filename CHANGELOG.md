# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2025-06-05

### Added

- PII interception and pseudonymization for outbound requests
- PII enrichment for inbound responses
- Local PII storage with PostgreSQL
- People CRUD with full PII handling
- Appointments CRUD with attendee PII handling
- Calendars, services, tags, and availability pass-through
- Webhook receiver with PII enrichment and relay
- Bearer token authentication (SHA256 hashed)
- Audit logging with configurable retention
- Email notifications via SMTP
- SMS notifications via Twilio and Vonage
- WhatsApp notifications via Evolution API and Meta Cloud API
- SQLAdmin panel at `/admin`
- Celery workers for async webhook relay and notifications
- Celery Beat for scheduled audit cleanup
- Docker Compose deployment (proxy, db, redis, worker, beat)
- Alembic database migrations
- Datacenter region support (BR, US, HOMOLOG)
- Health check endpoint
- Test suite with pytest (auth, audit, interceptor, enricher)
