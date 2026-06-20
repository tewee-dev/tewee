"""Email string marker type for dataclass fields.

Typical usage::

    from dataclasses import dataclass, field

    from tewee.api.email import EmailStr

    @dataclass
    class User:
        email: str = field(metadata={"type": EmailStr})

    user = User(email="me@example.com")
    EmailStr.validate(user)        # raises ValueError if the address is bad

The class is also callable on raw values, so it can be used without a
dataclass at all::

    >>> EmailStr("me@example.com")
    EmailStr('me@example.com')
    >>> EmailStr("not-an-email")
    Traceback (most recent call last):
        ...
    ValueError: Invalid email address: 'not-an-email'
"""

from __future__ import annotations

import re
from dataclasses import Field, fields, is_dataclass
from typing import Any, Iterator

__all__ = ["EmailStr"]

# A pragmatic, RFC-5321-ish pattern.  It is intentionally not fully RFC-5322
# compliant -- the goal is to catch obviously wrong values, not to fully
# validate every legal address.
_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)


class EmailStr(str):
    """A ``str`` subclass that validates the address on construction.

    Instances behave like normal strings, so they can be used anywhere a
    ``str`` is expected (JSON serialisation, file IO, ``%``-formatting, ...).
    The validation only runs once at construction time.

    Parameters
    ----------
    value:
        The email address to wrap.  Must be a ``str`` matching a basic
        email pattern.
    """

    __slots__ = ()

    def __new__(cls, value: Any) -> "EmailStr":
        if isinstance(value, EmailStr):
            return value
        if not isinstance(value, str):
            raise TypeError(
                f"EmailStr expected str, got {type(value).__name__}"
            )
        if not _EMAIL_PATTERN.match(value):
            raise ValueError(f"Invalid email address: {value!r}")
        return super().__new__(cls, value)

    @classmethod
    def validate(cls, instance: Any) -> None:
        """Validate every field of ``instance`` annotated with :class:`EmailStr`.

        Looks up the ``metadata["type"]`` entry for each dataclass field
        and verifies that fields tagged with :class:`EmailStr` actually
        contain a syntactically valid address.

        Raises
        ------
        TypeError
            If ``instance`` is not a dataclass instance.
        ValueError
            If any annotated field fails validation.  All fields are
            checked before raising so the caller sees every offender.
        """
        if not is_dataclass(instance):
            raise TypeError(
                f"{type(instance).__name__!s} is not a dataclass"
            )

        errors: list[str] = []
        for f in fields(instance):
            if f.metadata.get("type") is not cls:
                continue
            value = getattr(instance, f.name, None)
            try:
                cls(value)
            except (TypeError, ValueError) as exc:
                errors.append(
                    f"{type(instance).__name__}.{f.name}: {exc}"
                )
        if errors:
            raise ValueError(
                f"{len(errors)} field(s) failed EmailStr validation: "
                + "; ".join(errors)
            )

    @classmethod
    def iter_fields(cls, instance: Any) -> Iterator[tuple[Field[Any], "EmailStr"]]:
        """Yield ``(field, value)`` pairs for fields annotated with :class:`EmailStr`."""
        if not is_dataclass(instance):
            raise TypeError(f"{type(instance).__name__!s} is not a dataclass")
        for f in fields(instance):
            if f.metadata.get("type") is cls:
                yield f, cls(getattr(instance, f.name))
