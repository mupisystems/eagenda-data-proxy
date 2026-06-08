# Data Privacy

The Data Proxy provides built-in mechanisms for complying with data subject rights required by privacy regulations worldwide (GDPR, LGPD, CCPA, POPIA, PDPA, etc.).

## Overview

| Capability | Endpoint / Mechanism | Legal basis |
|------------|---------------------|-------------|
| Right to erasure | `DELETE /api/v3/people/{id}/forget/` | GDPR Art. 17, LGPD Art. 18 VI, CCPA §1798.105 |
| Data portability | `GET /api/v3/people/{id}/export/` | GDPR Art. 20, LGPD Art. 18 V |
| Automated purge | Celery beat task (daily) | GDPR Art. 5(1)(e), LGPD Art. 16 |

All privacy operations generate audit log entries for accountability.

## Right to Erasure

### `DELETE /api/v3/people/{external_id}/forget/`

Permanently deletes all local PII for a data subject. This is an irreversible operation.

### What is deleted

| Table | Records deleted |
|-------|----------------|
| `pii_person` | The person record (hard delete) |
| `pii_questionnaire_answer` | All answers linked to the person's appointments |
| `local_appointment` | All local appointment records for the person |
| `local_custom_data` | All custom data (person-level and appointment-level) |

### What is NOT deleted

- **Audit logs** — kept for legal accountability. The erasure itself is recorded as an `ERASURE` action in the audit log.
- **Cloud data** — the proxy sends a best-effort `PATCH` to eagendas cloud to pseudonymize the person's name to `[ERASED]` and clear email/phone. This may fail if the cloud API is unavailable, but local deletion proceeds regardless.

### Request

```http
DELETE /api/v3/people/ext-123/forget/
Authorization: Bearer <token>
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "erased",
  "summary": {
    "external_id": "ext-123",
    "person_deleted": true,
    "questionnaire_answers_deleted": 5,
    "appointments_deleted": 3,
    "custom_data_deleted": 2
  }
}
```

### Response when person not found

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "not_found",
  "message": "Person not found."
}
```

## Data Portability

### `GET /api/v3/people/{external_id}/export/`

Exports all data held about a person in machine-readable JSON format.

### What is included

| Section | Contents |
|---------|----------|
| `subject` | All PII fields: name, email, phone, identification, date of birth, address |
| `appointments` | All local appointment records with status and scheduled time |
| `questionnaire_answers` | All questionnaire answers linked to the person's appointments |
| `custom_data` | All custom data (person-level and appointment-level) |
| `audit_history` | Full history of actions performed on this person's data |
| `exported_at` | Timestamp of the export (UTC) |

### Request

```http
GET /api/v3/people/ext-123/export/
Authorization: Bearer <token>
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "subject": {
    "external_id": "ext-123",
    "person_key": "pk-abc-def",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+5511999999999",
    "identification_code": "123.456.789-00",
    "identification_type": "CPF",
    "date_of_birth": "1990-05-15",
    "address": {
      "street": "Rua Example, 100",
      "city": "Sao Paulo",
      "state": "SP",
      "postal_code": "01000-000"
    },
    "created_at": "2026-01-15T10:30:00-03:00",
    "updated_at": "2026-06-01T14:00:00-03:00"
  },
  "appointments": [
    {
      "appointment_key": "appt-001",
      "service_key": "srv-general",
      "scheduled_at": "2026-06-10T14:00:00-03:00",
      "status": "scheduled",
      "created_at": "2026-06-01T14:00:00-03:00"
    }
  ],
  "questionnaire_answers": [
    {
      "appointment_key": "appt-001",
      "question_key": "q-allergy",
      "question_text": "Do you have any allergies?",
      "answer_body": "Penicillin",
      "created_at": "2026-03-10T09:00:00-03:00"
    }
  ],
  "custom_data": {
    "person": { "vehicles": [{ "plate": "ABC-1234" }] },
    "appointment:appt-001": { "plate": "ABC-1234" }
  },
  "audit_history": [
    {
      "timestamp": "2026-06-07T10:00:00+00:00",
      "action": "EXPORT",
      "resource_type": "person",
      "resource_id": "pk-abc-def",
      "request_method": "GET",
      "request_path": "/api/v3/people/ext-123/export/",
      "pii_fields_accessed": null
    },
    {
      "timestamp": "2026-01-15T13:30:00+00:00",
      "action": "CREATE",
      "resource_type": "person",
      "resource_id": "pk-abc-def",
      "request_method": "POST",
      "request_path": "/api/v3/people/",
      "pii_fields_accessed": ["name", "email", "phone"]
    }
  ],
  "exported_at": "2026-06-07T10:00:00+00:00"
}
```

The export operation itself is audited as an `EXPORT` action.

## Automated Purge

The proxy automatically deletes PII records that have exceeded their retention period. This is enforced via the `purge_after` field on `pii_person`.

### How it works

1. A Celery beat task runs daily (`cleanup_expired_records`)
2. It finds all `pii_person` records where `purge_after <= today`
3. For each expired record, it performs a full erasure (same as the `/forget/` endpoint)
4. Each erasure is audited with `action: ERASURE` and `request_path: /system/purge`

### Setting the retention date

The `purge_after` field can be set in two ways:

**1. Via the API** when creating or updating a person:

```http
POST /api/v3/people/
Content-Type: application/json

{
  "external_id": "ext-123",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "purge_after": "2027-01-01"
}
```

**2. Via the admin panel** at `/admin/` under People (PII).

### Cleanup summary

The daily task also cleans up:
- **Audit logs** older than `audit_retention_days` (default: 365 days, configurable in `data_proxy_config.yml`)

### Monitoring

Check the Celery worker logs for purge activity:

```
INFO  Deleted 12 audit log entries older than 2025-06-07
INFO  Erasure completed for ext-old-1: person=True, answers=3, appointments=5
INFO  Erasure completed for ext-old-2: person=True, answers=0, appointments=2
```

## Audit Trail

All privacy operations generate audit log entries visible in the admin panel (`/admin/` > Audit Logs):

| Action | When |
|--------|------|
| `ERASURE` | Person data deleted (via `/forget/` or automated purge) |
| `EXPORT` | Person data exported (via `/export/`) |
| `CREATE` | Person created |
| `READ` | Person data accessed |
| `UPDATE` | Person data modified |

The audit log retains entries for `audit_retention_days` (default: 365). Even after a person is erased, their audit trail remains for the configured retention period to demonstrate compliance.

## Integration Guide

### Implementing a "Delete My Data" button

```python
import httpx

async def handle_delete_request(external_id: str):
    async with httpx.AsyncClient() as client:
        # 1. Export data first (recommended for confirmation)
        export = await client.get(
            f"https://proxy.local:8000/api/v3/people/{external_id}/export/",
            headers={"Authorization": "Bearer <token>"},
        )
        # Optionally: send export to the user via email

        # 2. Execute erasure
        response = await client.delete(
            f"https://proxy.local:8000/api/v3/people/{external_id}/forget/",
            headers={"Authorization": "Bearer <token>"},
        )
        return response.json()
```

### Setting retention at creation time

A common pattern is to set `purge_after` based on business rules when creating a person:

```python
from datetime import date, timedelta

# Retain for 2 years after creation
purge_date = date.today() + timedelta(days=730)

person_data = {
    "external_id": "ext-123",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "purge_after": purge_date.isoformat(),
}
```
