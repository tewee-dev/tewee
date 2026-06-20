"""Tests for :mod:`tewee.api.email`."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from tewee.api.email import EmailStr


# ---------------------------------------------------------------------------
# Construction behaviour
# ---------------------------------------------------------------------------


def test_email_str_accepts_valid_address() -> None:
    e = EmailStr("user@example.com")
    assert isinstance(e, str)        # behaves like a string
    assert str(e) == "user@example.com"


def test_email_str_is_idempotent() -> None:
    e = EmailStr("user@example.com")
    assert EmailStr(e) is e          # wrapping twice is a no-op


@pytest.mark.parametrize(
    "value",
    [
        "no-at-sign",
        "two@@signs.com",
        "user@",
        "@example.com",
        "user@example",
        "user@@@example..com",
        "",
        "spaces in@example.com",
    ],
)
def test_email_str_rejects_invalid_addresses(value: str) -> None:
    with pytest.raises(ValueError):
        EmailStr(value)


@pytest.mark.parametrize("value", [123, 1.5, None, ["a@b"], {"a@b"}])
def test_email_str_rejects_non_strings(value: object) -> None:
    with pytest.raises(TypeError):
        EmailStr(value)


# ---------------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------------


@dataclass
class _User:
    email: str = field(metadata={"type": EmailStr})


def test_validate_accepts_a_valid_instance() -> None:
    EmailStr.validate(_User(email="me@example.com"))


def test_validate_raises_for_an_invalid_instance() -> None:
    with pytest.raises(ValueError, match="_User.email"):
        EmailStr.validate(_User(email="not-an-email"))


def test_validate_rejects_non_dataclass() -> None:
    with pytest.raises(TypeError):
        EmailStr.validate("not-a-dataclass")


@dataclass
class _Mixed:
    name: str
    email: str = field(metadata={"type": EmailStr})


def test_iter_fields_only_yields_annotated_ones() -> None:
    instance = _Mixed(name="Alice", email="alice@example.com")
    annotated = list(EmailStr.iter_fields(instance))
    assert [f.name for f, _ in annotated] == ["email"]
    field_obj, value = annotated[0]
    assert value == "alice@example.com"
    assert field_obj.name == "email"


def test_iter_fields_rejects_non_dataclass() -> None:
    with pytest.raises(TypeError):
        list(EmailStr.iter_fields("nope"))


# ---------------------------------------------------------------------------
# Re-export from the top-level package
# ---------------------------------------------------------------------------


def test_email_str_is_exposed_at_package_root() -> None:
    import tewee
    import tewee.api

    assert tewee.EmailStr is tewee.api.EmailStr is EmailStr
