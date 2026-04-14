"""
Domain models — plain Python dataclasses with no ORM or framework imports.

These are the objects that travel between layers (repository → service → router).
Every layer speaks this language, so swapping the database never touches the
service or router layers.

  id = 0  means "not yet saved to the database".
  The repository sets the real ID after persisting the record.
"""
from dataclasses import dataclass


@dataclass
class UserData:
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    hashed_password: str
    is_active: bool
    role: str
    phone_number: str | None


@dataclass
class TodoData:
    id: int
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int
