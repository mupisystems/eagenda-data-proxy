from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    """Standard eagendas paginated response."""

    count: int = 0
    next: str | None = None
    previous: str | None = None
    results: list[dict] = []
