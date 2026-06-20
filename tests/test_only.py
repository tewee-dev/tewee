"""Tests for :mod:`tewee.api.only`."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from tewee.api.email import EmailStr
from tewee.api.only import Only


# ---------------------------------------------------------------------------
# Construction behaviour
# ---------------------------------------------------------------------------


def test_only_requires_at_least_one_value() -> None:
    with pytest.raises(ValueError, match="at least one"):
        Only()


def test_only_stores_allowed_values() -> None:
    o = Only("a", "b", "c")
    assert o.allowed == ("a", "b", "c")


def test_only_deduplicates_preserving_first_occurrence() -> None:
    o = Only("a", "b", "a", "c", "b")
    assert o.allowed == ("a", "b", "c")


def test_only_supports_mixed_types() -> None:
    # Note: 1, 1.0 and True all compare equal in Python, so we use
    # values that are actually distinct.
    o = Only(1, "1", 1.5, "two", None)
    assert o.allowed == (1, "1", 1.5, "two", None)


def test_only_repr_contains_values() -> None:
    assert repr(Only("a", "b")) == "Only('a', 'b')"


def test_only_equality_is_value_based() -> None:
    assert Only("a", "b") == Only("a", "b")
    assert Only("a", "b") != Only("a", "c")
    assert Only("a", "b") != "not-an-only"


def test_only_is_hashable() -> None:
    o = Only("a", "b")
    assert hash(o) == hash(Only("a", "b"))
    # Usable as a dict key / set member
    lookup = {o: "marker"}
    assert lookup[Only("a", "b")] == "marker"


# ---------------------------------------------------------------------------
# Direct value checking
# ---------------------------------------------------------------------------


def test_only_call_accepts_allowed_value() -> None:
    o = Only("admin", "user", "guest")
    assert o("admin") == "admin"


def test_only_call_returns_value_unchanged() -> None:
    obj = object()
    o = Only(obj, "other")
    assert o(obj) is obj


def test_only_call_rejects_unknown_value() -> None:
    o = Only("admin", "user", "guest")
    with pytest.raises(ValueError, match="'superuser'"):
        o("superuser")


def test_only_contains_operator() -> None:
    o = Only(1, 2, 3)
    assert 1 in o
    assert 4 not in o


def test_only_supports_falsy_allowed_values() -> None:
    o = Only(0, "", False, None)
    # All of these should be accepted, not interpreted as "no values".
    assert o(0) == 0
    assert o("") == ""
    assert o(False) is False
    assert o(None) is None


# ---------------------------------------------------------------------------
# from_iterable convenience
# ---------------------------------------------------------------------------


def test_from_iterable_works() -> None:
    o = Only.from_iterable(range(3))
    assert o.allowed == (0, 1, 2)
    assert o(2) == 2


def test_from_iterable_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        Only.from_iterable([])


# ---------------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------------


@dataclass
class _User:
    role: str = field(metadata={"type": Only("admin", "user", "guest")})
    plan: int = field(metadata={"type": Only(1, 2, 3)}, default=2)


def test_validate_accepts_a_valid_instance() -> None:
    Only.validate(_User(role="admin", plan=1))


def test_validate_raises_for_invalid_string_field() -> None:
    with pytest.raises(ValueError, match="_User.role"):
        Only.validate(_User(role="superuser", plan=2))


def test_validate_raises_for_invalid_int_field() -> None:
    with pytest.raises(ValueError, match="_User.plan"):
        Only.validate(_User(role="admin", plan=99))


def test_validate_reports_all_offending_fields() -> None:
    with pytest.raises(ValueError) as excinfo:
        Only.validate(_User(role="superuser", plan=99))
    msg = str(excinfo.value)
    assert "_User.role" in msg
    assert "_User.plan" in msg
    assert "2 field(s) failed" in msg


def test_validate_rejects_non_dataclass() -> None:
    with pytest.raises(TypeError):
        Only.validate("not-a-dataclass")


@dataclass
class _Mixed:
    name: str
    role: str = field(metadata={"type": Only("admin", "user")})


def test_iter_fields_only_yields_annotated_ones() -> None:
    instance = _Mixed(name="Alice", role="admin")
    annotated = list(Only.iter_fields(instance))
    assert [f.name for f, _ in annotated] == ["role"]
    field_obj, value = annotated[0]
    assert value == "admin"
    assert field_obj.name == "role"


def test_iter_fields_rejects_non_dataclass() -> None:
    with pytest.raises(TypeError):
        list(Only.iter_fields("nope"))


# ---------------------------------------------------------------------------
# Coexistence with EmailStr
# ---------------------------------------------------------------------------


@dataclass
class _Combined:
    email: str = field(metadata={"type": EmailStr})
    role: str = field(metadata={"type": Only("admin", "user")})


def test_only_and_email_str_can_coexist() -> None:
    _Combined(email="me@example.com", role="admin")  # construction is fine

    # EmailStr's own validator should ignore the role field.
    EmailStr.validate(_Combined(email="me@example.com", role="admin"))

    # Only's own validator should ignore the email field.
    Only.validate(_Combined(email="me@example.com", role="admin"))


def test_only_validator_does_not_touch_unannotated_fields() -> None:
    @dataclass
    class WithUntagged:
        allowed: int = field(metadata={"type": Only(1, 2)})
        free: str = "anything goes"

    instance = WithUntagged(allowed=1, free="totally not whitelisted")
    Only.validate(instance)  # no error -- `free` is not annotated


# ---------------------------------------------------------------------------
# Type-whitelist mode: Only[int, str]
# ---------------------------------------------------------------------------


def test_subscript_returns_type_whitelist() -> None:
    o = Only[int, str]
    assert o.is_type_check is True  # type: ignore[comparison-overlap]
    assert o.allowed == (int, str)


def test_subscript_single_type() -> None:
    o = Only[int]
    assert o.is_type_check is True  # type: ignore[comparison-overlap]
    assert o.allowed == (int,)


def test_subscript_rejects_non_types() -> None:
    with pytest.raises(TypeError, match="requires type arguments"):
        Only[1, 2]
    with pytest.raises(TypeError, match="requires type arguments"):
        Only["not-a-type"]


def test_type_whitelist_repr_uses_brackets() -> None:
    assert repr(Only[int, str]) == "Only[int, str]"
    assert repr(Only[int]) == "Only[int]"


def test_type_whitelist_value_whitelist_have_distinct_reprs() -> None:
    assert repr(Only("a", "b")) == "Only('a', 'b')"
    assert repr(Only[int, str]) == "Only[int, str]"
    # They should not be equal to each other.
    assert Only("a") != Only[str]


def test_type_whitelist_accepts_matching_type() -> None:
    assert Only[int, str](42) == 42
    assert Only[int, str]("hello") == "hello"


def test_type_whitelist_rejects_non_matching_type() -> None:
    with pytest.raises(TypeError, match="is not an instance of any of"):
        Only[int, str](3.14)
    with pytest.raises(TypeError, match="is not an instance of any of"):
        Only[int, str](None)


def test_type_whitelist_in_operator_uses_isinstance() -> None:
    # Assign to a local first so the static type checker sees an
    # ``Only`` instance, not a parameterized class.
    o: Only = Only[int, str]
    assert 5 in o
    assert "x" in o
    assert 3.14 not in o


def test_type_whitelist_eq_is_mode_aware() -> None:
    a: Only = Only[int, str]
    b: Only = Only[int, str]
    c: Only = Only[int]
    d: Only = Only(int)
    assert a == b
    assert a != Only.__class_getitem__((str, int))  # order matters
    assert c != d                                   # different modes


def test_type_whitelist_is_hashable() -> None:
    a: Only = Only[int, str]
    b: Only = Only[int, str]
    assert hash(a) == hash(b)
    # Usable as a dict key.
    lookup: dict[Only, str] = {a: "marker"}
    assert lookup[b] == "marker"


def test_type_whitelist_supports_subclass_match() -> None:
    class MyInt(int):
        pass

    assert Only[int, str](MyInt(5)) == MyInt(5)


def test_type_whitelist_from_types_helper() -> None:
    a = Only.from_types(int, str)
    b = Only[int, str]
    assert a == b
    assert a.is_type_check is True


def test_type_whitelist_from_types_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        Only.from_types()


# ---------------------------------------------------------------------------
# Type-annotation usage on dataclass fields
# ---------------------------------------------------------------------------


@dataclass
class _Annotated:
    # ``Only[int, str]`` here is a runtime *value* (the type-whitelist
    # returned by ``__class_getitem__``).  We annotate the field as
    # ``object`` so the static type checker is happy; at runtime the
    # ``field`` default below produces a real ``Only`` instance.
    name: str = field(metadata={"type": Only[int, str]})


def test_only_works_as_module_level_annotation() -> None:
    # A module-level annotation shows that ``Only[int, str]`` is a
    # valid Python expression.  We use ``cast`` so the static type
    # checker treats the value as a real ``Only`` instance.
    from typing import cast

    marker = cast(Only, Only[int, str])
    assert marker == Only[int, str]
    assert marker(42) == 42
    assert marker("hi") == "hi"
    with pytest.raises(TypeError):
        marker(3.14)


def test_validate_runs_against_metadata_marker() -> None:
    Only.validate(_Annotated(name="ok"))
    with pytest.raises(ValueError, match="_Annotated.name"):
        Only.validate(_Annotated(name=3.14))   # type: ignore[arg-type]


def test_type_whitelist_iter_fields() -> None:
    instance = _Annotated(name="hello")
    annotated = list(Only.iter_fields(instance))
    assert [f.name for f, _ in annotated] == ["name"]
    field_obj, value = annotated[0]
    assert value == "hello"
    assert field_obj.name == "name"


def test_only_subscript_works_in_dataclass_field_default() -> None:
    @dataclass
    class _Defaults:
        marker: object = field(default=Only[int, str])

    assert _Defaults().marker == Only[int, str]


# ---------------------------------------------------------------------------
# Re-export from the top-level package
# ---------------------------------------------------------------------------


def test_only_is_exposed_at_package_root() -> None:
    import tewee
    import tewee.api

    assert tewee.Only is tewee.api.Only is Only
