from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    created_at: datetime  # default value is set in a create table query
    id: int = None
    chat_id: int = None
    is_admin: bool = False
    first_name: str = None
    last_name: str = None
    last_updated: datetime = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return User(**d)
