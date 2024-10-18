from dataclasses import dataclass, asdict, fields
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    created_at: datetime  # default value is set in a create table query
    id: int = None
    used_bot: bool = False
    blocked_bot: bool = False
    is_admin: bool = False
    first_name: str = None
    last_name: str = None
    last_updated: datetime = None

    def to_dict(self) -> dict:
        # a dict of class_field: field_value pairs
        fields_dict = {f.name: self.__getattribute__(f.name) for f in fields(self)}
        # as MySQL stores bool values as 0s and 1s we manually transform bool fields
        bool_fields = self._get_bool_fields()
        return {k: (v if k not in bool_fields else bool(v)) for k, v in fields_dict.items()}

    @classmethod
    def from_dict(cls, d: dict) -> 'User':
        return User(**d)

    @classmethod
    def _get_bool_fields(cls) -> tuple[str]:
        return tuple(f.name for f in fields(cls) if f.type == bool)