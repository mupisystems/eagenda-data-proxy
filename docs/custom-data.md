# Custom Data

The Data Proxy allows storing arbitrary custom fields locally, associated with persons or appointments. This data is never sent to eagendas cloud and can be consumed by other systems via dedicated endpoints.

## Use Cases

- Vehicle data for inspection appointments (plate, color, year, model)
- Insurance information linked to a person
- Internal reference numbers or codes
- Any domain-specific data that should stay on-premise

## How It Works

### On appointment creation

When creating an appointment, include a `custom_data` field in the payload. The proxy strips it before forwarding to eagendas and stores it locally:

```http
POST /api/v3/appointments/
Content-Type: application/json

{
  "calendar_key": "b1c2d3e4-...",
  "service_list": [{ "service_key": "f5a6b7c8-..." }],
  "start": { "dateTime": "2026-06-10T14:00:00-03:00" },
  "attendees": [
    {
      "external_id": "ext-123",
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  ],
  "custom_data": {
    "plate": "ABC-1234",
    "color": "white",
    "year": 2022,
    "model": "Civic"
  }
}
```

The payload follows the eagendas shape: person data lives inside `attendees`, the start time is `start.dateTime`, and services are listed in `service_list`. `custom_data` is a proxy-only extension — it is stripped before forwarding. The proxy strips each attendee's PII and keys local records off the attendee's `external_id`.

What happens:
1. `custom_data` is removed from the payload
2. Each attendee's PII is stripped/pseudonymized and stored locally
3. The rest is forwarded to eagendas cloud
4. After successful creation (201), `custom_data` is saved locally linked to the `appointment_key`

### On appointment retrieval

Custom data is automatically merged back into the response:

```http
GET /api/v3/appointments/appt-001/
```

```json
{
  "appointment_key": "appt-001",
  "status": "PENDING",
  "calendar": { "calendar_key": "b1c2d3e4-...", "calendar_name": "Vistoria" },
  "service_list": [{ "service_key": "f5a6b7c8-...", "service_name": "Vistoria" }],
  "start": { "dateTime": "2026-06-10T14:00:00-03:00", "timeZone": "America/Sao_Paulo" },
  "attendees": [
    {
      "person_key": "a1b2c3d4-...",
      "external_id": "ext-123",
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  ],
  "custom_data": {
    "plate": "ABC-1234",
    "color": "white",
    "year": 2022,
    "model": "Civic"
  }
}
```

This also works for paginated listing (`GET /api/v3/appointments/`).

## Direct Access Endpoints

Other systems can read and write custom data directly, without going through the appointment flow.

### Person custom data

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/api/v3/local-data/person/{external_id}/` | Read custom data |
| `PUT` | `/api/v3/local-data/person/{external_id}/` | Replace (overwrite) |
| `PATCH` | `/api/v3/local-data/person/{external_id}/` | Merge with existing |
| `DELETE` | `/api/v3/local-data/person/{external_id}/` | Delete |

### Appointment custom data

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/api/v3/local-data/appointment/{appointment_key}/` | Read custom data |
| `PUT` | `/api/v3/local-data/appointment/{appointment_key}/` | Replace (overwrite) |
| `PATCH` | `/api/v3/local-data/appointment/{appointment_key}/` | Merge with existing |
| `DELETE` | `/api/v3/local-data/appointment/{appointment_key}/` | Delete |

All endpoints require Bearer token authentication.

### PUT vs PATCH

- **PUT** replaces the entire `data` JSON. Use when you have the complete object.
- **PATCH** does a shallow merge (`{**existing, **new}`). Use to add or update specific fields without losing the rest.

Example:

```
# Existing data: { "plate": "ABC-1234", "color": "white" }

PATCH /api/v3/local-data/appointment/appt-001/
{ "year": 2022 }

# Result: { "plate": "ABC-1234", "color": "white", "year": 2022 }
```

Note: PATCH merge is **shallow**. For nested objects or arrays, the new value replaces the old one entirely at that key. To update a list (e.g., vehicles), send the full list via PUT.

### Response format

```json
{
  "entity_type": "appointment",
  "entity_key": "appt-001",
  "data": {
    "plate": "ABC-1234",
    "color": "white",
    "year": 2022
  }
}
```

## Multiple Items per Person

A person can have custom data at two levels:

**Person-level** — shared across all appointments (e.g., a list of vehicles):

```http
PUT /api/v3/local-data/person/ext-123/
{
  "vehicles": [
    { "plate": "ABC-1234", "color": "white", "year": 2022, "model": "Civic" },
    { "plate": "XYZ-5678", "color": "black", "year": 2024, "model": "Corolla" }
  ]
}
```

**Appointment-level** — specific to one appointment (e.g., which vehicle was used):

```http
POST /api/v3/appointments/
{
  "calendar_key": "b1c2d3e4-...",
  "service_list": [{ "service_key": "f5a6b7c8-..." }],
  "start": { "dateTime": "2026-06-10T14:00:00-03:00" },
  "attendees": [
    { "external_id": "ext-123", "name": "Jane Doe" }
  ],
  "custom_data": {
    "plate": "ABC-1234",
    "color": "white",
    "year": 2022
  }
}
```

This way, a frontend can:
1. Fetch the person's vehicles from `GET /api/v3/local-data/person/ext-123/`
2. Let the user pick one
3. Send the selected vehicle as `custom_data` in the appointment creation

## Integration Example

A vehicle inspection system querying the proxy:

```python
import httpx

PROXY = "https://proxy.local:8000"
HEADERS = {"Authorization": "Bearer <token>"}

async def get_appointment_with_vehicle(appointment_key: str):
    async with httpx.AsyncClient() as client:
        # Single call returns: appointment + PII + custom data
        resp = await client.get(
            f"{PROXY}/api/v3/appointments/{appointment_key}/",
            headers=HEADERS,
        )
        data = resp.json()

        # data["attendees"][0]["name"]  -> from local PII store
        # data["attendees"][0]["email"] -> from local PII store
        # data["custom_data"]           -> from local custom data
        # data["date_time"]             -> from eagendas cloud
        return data


async def register_vehicle_for_person(external_id: str, vehicles: list):
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{PROXY}/api/v3/local-data/person/{external_id}/",
            headers=HEADERS,
            json={"vehicles": vehicles},
        )
        return resp.json()
```

## Data Privacy

Custom data is fully integrated with the privacy features:

- **Right to erasure** (`DELETE /api/v3/people/{id}/forget/`) deletes all custom data for the person (both person-level and appointment-level)
- **Data export** (`GET /api/v3/people/{id}/export/`) includes all custom data in the export
- **Automated purge** cleans up custom data when a person's `purge_after` date is reached

## Admin Panel

Custom data records are visible in the admin panel (`/admin/`) under **Custom Data**, where you can:

- Browse all records by entity type and key
- Search by `entity_key`
- View and edit the JSON data

## Database Table

The `local_custom_data` table stores one record per entity:

| Column | Type | Description |
|--------|------|-------------|
| `entity_type` | string(20) | `person` or `appointment` |
| `entity_key` | string(255) | `external_id` or `appointment_key` |
| `data` | JSON | Arbitrary key-value data |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |

A unique index on `(entity_type, entity_key)` ensures one record per entity.

To apply the migration:

```bash
alembic upgrade head
```
