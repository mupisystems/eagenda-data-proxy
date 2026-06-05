"""Test data factories."""


def make_person_body(**overrides) -> dict:
    defaults = {
        "name": "Maria Santos",
        "email": "maria@example.com",
        "phone": "+5511999997777",
        "identification_code": "12345678900",
        "identification_type": "CPF",
        "external_id": "EXT-001",
    }
    defaults.update(overrides)
    return defaults


def make_cloud_person_response(**overrides) -> dict:
    defaults = {
        "person_key": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "Citizen-EXT-001",
        "external_id": "EXT-001",
    }
    defaults.update(overrides)
    return defaults


def make_appointment_response(**overrides) -> dict:
    defaults = {
        "appointment_key": "x1y2z3-appt-key",
        "status": "CONFIRMED",
        "calendar": {"calendar_key": "cal-123", "calendar_name": "Vistoria"},
        "attendees": [
            {
                "person_key": "a1b2c3d4",
                "name": "Citizen-EXT-001",
                "external_id": "EXT-001",
            }
        ],
        "start": {"dateTime": "2026-06-15T10:00:00-03:00", "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": "2026-06-15T11:00:00-03:00", "timeZone": "America/Sao_Paulo"},
    }
    defaults.update(overrides)
    return defaults
