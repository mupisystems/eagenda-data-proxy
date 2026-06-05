"""PII field definitions and classification rules."""

# Person fields that contain PII.
# "pseudonymize" = replace with a generated value; "strip" = remove entirely from cloud payload.
PERSON_PII_FIELDS: dict[str, dict] = {
    "name": {"action": "pseudonymize"},
    "email": {"action": "strip"},
    "phone": {"action": "strip"},
    "identification_code": {"action": "strip"},
    "identification_type": {"action": "strip"},
    "date_of_birth": {"action": "strip"},
}

# Fields that are operational (always forwarded to cloud as-is)
PERSON_PASSTHROUGH_FIELDS = {"external_id", "person_key"}

# Question types whose answers are classified as PII
DEFAULT_QUESTIONNAIRE_PII_TYPES = {"text", "short-text", "paragraph"}


def is_pii_field(field_name: str) -> bool:
    """Check if a person field is PII."""
    return field_name in PERSON_PII_FIELDS


def get_pii_field_names() -> list[str]:
    """Return list of PII field names."""
    return list(PERSON_PII_FIELDS.keys())
