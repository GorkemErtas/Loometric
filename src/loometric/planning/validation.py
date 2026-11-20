"""Small strict validation primitives shared only by the planning domain."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TypeVar


class PlanningError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def text(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(ord(c) < 32 for c in value)
    ):
        raise PlanningError("INVALID_IDENTIFIER", f"{field} must be a nonblank canonical string.")


def integer(value: int, field: str, *, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise PlanningError("INVALID_INTEGER", f"{field} must be an integer >= {minimum}.")


def decimal(value: Decimal, field: str, *, positive: bool = False) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
        or (positive and value == 0)
    ):
        raise PlanningError(
            "INVALID_DECIMAL",
            f"{field} requires a finite {'positive' if positive else 'nonnegative'} Decimal.",
        )


def calendar_date(value: date, field: str) -> None:
    if type(value) is not date:
        raise PlanningError("INVALID_DATE", f"{field} must be a calendar date, not a datetime.")


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PlanningError("INVALID_TIMESTAMP", "Interval timestamps must be timezone-aware.")
    return value.astimezone(UTC)


E = TypeVar("E", bound=StrEnum)
T = TypeVar("T")


def enum_value(value: E, enum_type: type[E], field: str) -> None:
    if not isinstance(value, enum_type):
        raise PlanningError("INVALID_ENUM", f"{field} must be a {enum_type.__name__} value.")


def members(
    value: tuple[T, ...], item_type: type[T], field: str, *, nonempty: bool = False
) -> None:
    if (
        type(value) is not tuple
        or (nonempty and not value)
        or any(not isinstance(item, item_type) for item in value)
    ):
        raise PlanningError(
            "INVALID_COLLECTION",
            f"{field} must be an immutable tuple of {item_type.__name__} values.",
        )
