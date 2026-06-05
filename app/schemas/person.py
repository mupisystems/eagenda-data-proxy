from pydantic import BaseModel, EmailStr


class PersonCreate(BaseModel):
    """Person creation payload from client."""
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None


class PersonUpdate(BaseModel):
    """Person update payload from client."""
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    identification_code: str | None = None
    identification_type: str | None = None
    external_id: str | None = None
