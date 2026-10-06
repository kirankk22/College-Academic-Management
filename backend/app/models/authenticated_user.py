from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    email: str | None
    role: str
    organization_id: UUID | None
    institution_id: UUID | None
    department_id: UUID | None
    is_active: bool