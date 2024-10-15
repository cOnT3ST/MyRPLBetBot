from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    id: int = None
    chat_id: int = None
    is_auth: bool = False
    is_admin: bool = False
    created_at: datetime = None
    first_name: str = None
    last_name: str = None
    last_updated: datetime = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return User(**d)
