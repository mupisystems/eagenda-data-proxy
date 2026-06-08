from pydantic import BaseModel, ConfigDict


class PersonCreate(BaseModel):
    """Person creation payload from client.

    ``extra="allow"`` keeps any unmodeled fields so the proxy forwards the
    client's payload to eagendas untouched (use ``model_dump(exclude_unset=True)``).
    """

    model_config = ConfigDict(extra="allow")

    name: str
    email: str | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None


class PersonUpdate(BaseModel):
    """Person update payload from client."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None
