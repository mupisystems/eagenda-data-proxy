# Booking Limits

The Data Proxy allows configuring appointment limit rules per client, controlling:

- Maximum number of simultaneous future appointments
- Progressive no-show penalties (escalating block periods)
- Cooldown between bookings (anti-spam)
- Custom rules per service, tag, or dynamic condition

## How It Works

Every attempt to create an appointment (`POST /api/v3/appointments/`) goes through a limit check before being forwarded to eAgendas. If the client is blocked, the response returns `HTTP 429` with an explanatory message.

### Flow

```
POST /appointments/
  |
  v
[1] limiter.check(external_id, service_key, tag)
  |  (queries local_appointment table for real-time counts)
  |
  |-- Blocked? --> 429 { error, message, details }
  |
  v
[2] Intercept PII, forward to cloud
  |
  v
[3] Success (201) --> record local_appointment (status=scheduled)
```

Appointment statuses are updated automatically via webhooks:

| Webhook event     | Local status update |
|-------------------|---------------------|
| `NO_SHOW`         | `status → noshow`   |
| `COMPLETED`       | `status → completed` |
| `CANCELED`        | `status → canceled`  |

All limit checks are **query-based** — derived from the `local_appointment` table in real-time, not from fragile counters. This ensures accurate counts even when appointments span long time windows.

## Configuration

Edit the `booking_limits.json` file at the project root. Changes are applied automatically without restart (cached by file mtime).

### Structure

```json
{
  "enabled": true,
  "defaults": { ... },
  "rules": [ ... ],
  "messages": { ... }
}
```

### `enabled`

Enables or disables the entire booking limits feature. When `false`, no checks are performed.

### `defaults`

Base rule applied to all clients:

```json
{
  "max_future_appointments": 3,
  "noshow_window_days": 90,
  "cooldown_minutes": 0,
  "noshow_penalties": [
    { "from": 1, "block_days": 7 },
    { "from": 2, "block_days": 14 },
    { "from": 3, "block_days": 30 },
    { "from": 5, "block_days": 90, "max_future_appointments": 1 }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `max_future_appointments` | int | Maximum number of simultaneous confirmed future appointments |
| `noshow_window_days` | int | Window in days to consider no-shows. Older no-shows are ignored |
| `cooldown_minutes` | int | Minimum time between bookings (0 = no cooldown) |
| `noshow_penalties` | list | List of progressive penalties (see below) |

### `noshow_penalties`

Ordered list of penalty tiers. The system applies the most severe tier the client has reached:

```json
[
  { "from": 1, "block_days": 7 },
  { "from": 2, "block_days": 14 },
  { "from": 3, "block_days": 30 },
  { "from": 5, "block_days": 90, "max_future_appointments": 1 }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `from` | int | Minimum number of no-shows to activate this tier |
| `block_days` | int | Days of blocking from the last no-show date |
| `max_future_appointments` | int | (optional) Overrides the future appointments limit for this tier |

#### Practical example

With the default configuration:

| No-shows | Tier applied  | Block period | Future limit  |
|----------|---------------|--------------|---------------|
| 0        | none          | --           | 3 (default)   |
| 1        | `from: 1`     | 7 days       | 3             |
| 2        | `from: 2`     | 14 days      | 3             |
| 3-4      | `from: 3`     | 30 days      | 3             |
| 5+       | `from: 5`     | 90 days      | **1**         |

The block period is counted from the date of the last no-show (`last_noshow_at`). After the block period expires, the client can book again (respecting the future appointments limit).

### `rules`

List of specific rules that override the defaults. The **first rule** whose `match` criteria corresponds to the context is applied:

```json
{
  "rules": [
    {
      "name": "VIP - no restrictions",
      "match": { "tag": "vip" },
      "max_future_appointments": 10,
      "noshow_penalties": []
    },
    {
      "name": "Dentistry - stricter",
      "match": { "service_key": "srv-dentistry" },
      "max_future_appointments": 1,
      "noshow_penalties": [
        { "from": 1, "block_days": 14 },
        { "from": 2, "block_days": 30, "max_future_appointments": 0 }
      ]
    },
    {
      "name": "Repeat offender",
      "match": { "noshow_count__gte": 5 },
      "max_future_appointments": 1,
      "noshow_penalties": [
        { "from": 5, "block_days": 180 }
      ]
    }
  ]
}
```

#### Match criteria

| Criterion | Description | Example |
|-----------|-------------|---------|
| `service_key` | Service key in eAgendas | `"srv-dentistry"` |
| `tag` | Client tag | `"vip"` |
| `<field>__gte` | Greater than or equal to | `"noshow_count__gte": 5` |
| `<field>__lte` | Less than or equal to | `"noshow_count__lte": 1` |

Multiple criteria in the same `match` use AND logic (all must be true).

To disable penalties in a rule, use `"noshow_penalties": []`.

### `messages`

Message templates returned to the client in the `429` response:

```json
{
  "messages": {
    "future_limit_reached": "You already have {count}/{max} future appointments.",
    "noshow_blocked": "Due to {noshow_count} missed appointment(s), new bookings are blocked until {unblock_date}.",
    "cooldown_active": "Please wait {minutes} minutes between bookings."
  }
}
```

#### Available placeholders

| Message | Placeholders |
|---------|-------------|
| `future_limit_reached` | `{count}` (current), `{max}` (limit) |
| `noshow_blocked` | `{noshow_count}`, `{unblock_date}` (DD/MM/YYYY) |
| `cooldown_active` | `{minutes}` |

## Denial Response

When a booking is denied, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": "noshow_blocked",
  "message": "Due to 3 missed appointment(s), new bookings are blocked until 07/15/2026.",
  "details": {
    "noshow_count": 3,
    "block_until": "2026-07-15T10:30:00-03:00"
  }
}
```

Possible `error` values:

| Value | Cause |
|-------|-------|
| `noshow_blocked` | Blocked due to no-show penalty |
| `future_limit_reached` | Future appointments limit reached |
| `cooldown_active` | Cooldown between bookings still active |

## Admin Panel

Appointment records are visible in the admin panel (`/admin/`) under the **Local Appointments** section, where you can:

- View all tracked appointments with `appointment_key`, `external_id`, `service_key`, `scheduled_at`, `status`
- Search by `appointment_key` or `external_id`
- Manually edit status (e.g., reset a no-show after a client appeal)

## Database Table

The `local_appointment` table stores one record per appointment:

| Column | Type | Description |
|--------|------|-------------|
| `appointment_key` | string | Unique appointment identifier (from eAgendas) |
| `external_id` | string | Client identifier (same as `pii_person`) |
| `service_key` | string | Service key (optional) |
| `scheduled_at` | datetime | Scheduled date/time of the appointment |
| `status` | string | Current status: `scheduled`, `completed`, `canceled`, `noshow` |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last status update |

All limit checks are derived from queries on this table:

| Check | Query |
|-------|-------|
| Future appointments | `WHERE external_id = ? AND status = 'scheduled' AND scheduled_at > now()` |
| No-shows in window | `WHERE external_id = ? AND status = 'noshow' AND updated_at >= now() - window_days` |
| Cooldown | `WHERE external_id = ? ORDER BY created_at DESC LIMIT 1` |

To apply the migration:

```bash
alembic upgrade head
```
