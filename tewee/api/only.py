"""``Only[...]`` marker for dataclass fields that accept a fixed set of values.

``Only`` supports two complementary modes that can both be used as
**type annotations** on dataclass fields and as ``field(metadata=...)``
markers:

1. **Value whitelist** -- built with ``Only("a", "b", "c")``: the value
   must be one of the supplied specific values.

   ::

       @dataclass
       class User:
           role: str = field(metadata={"type": Only("admin", "user", "guest")})
           plan: int = field(metadata={"type": Only(1, 2, 3)}, default=2)

2. **Type whitelist** -- built with ``Only[int, str]``: the value must
   be an instance of one of the supplied types.  Because this is just
   regular Python subscript syntax, it works naturally as a *type
   annotation*::

       @dataclass
       class User:
           role: Only[int, str] = 5          # type-annotated
           email: str = field(metadata={"type": Only[int, str]})  # metadata form

The instance is also callable on raw values, so it can be used without
a dataclass at all::

    >>> role = Only("admin", "user", "guest")
    >>> role("admin")
    'admin'
    >>> role("superuser")
    Traceback (most recent call last):
        ...
    ValueError: Value 'superuser' is not one of ('admin', 'guest', 'user')

    >>> id_type = Only[int, str]
    >>> id_type(42)
    42
    >>> id_type(3.14)
    Traceback (most recent call last):
        ...
    TypeError: Value 3.14 is not an instance of any of ('int', 'str')
"""

from __future__ import annotations

from dataclasses import Field, fields, is_dataclass
from typing import Any, Iterable, Iterator, Sequence

__all__ = ["Only"]

# Sentinel used to distinguish "no allowed values supplied" from
# "a single falsy allowed value supplied" (e.g. ``Only(0)`` or ``Only("")``).
_MISSING: Any = object()


class Only:
    """A validator that only accepts values from a fixed whitelist.

    Two construction styles are supported:

    * ``Only("a", "b", "c")`` -- **value whitelist**.  The value must be
      one of the supplied concrete values.
    * ``Only[int, str]`` -- **type whitelist**.  The value must be an
      instance of one of the supplied types.  This uses standard Python
      subscript syntax and works as a type annotation.

    Both styles are interchangeable as ``metadata["type"]`` markers on
    dataclass fields and as direct callables.  Equality and hashing are
    based on the configured whitelist **and** the mode, so two ``Only``
    instances configured the same way compare equal and can be used
    interchangeably.
    """

    __slots__ = ("_allowed", "_is_type_check")

    def __init__(self, *allowed: Any) -> None:
        if not allowed:
            raise ValueError(
                "Only() requires at least one allowed value; "
                "use Any if you want to accept everything"
            )
        # Keep the order stable but de-duplicate by equality.
        seen: list[Any] = []
        for value in allowed:
            if value not in seen:
                seen.append(value)
        self._allowed: tuple[Any, ...] = tuple(seen)
        self._is_type_check: bool = False

    # ------------------------------------------------------------------
    # Type-whitelist construction: ``Only[int, str]``
    # ------------------------------------------------------------------

    @classmethod
    def __class_getitem__(cls, types: Any) -> "Only":
        """Support ``Only[T1, T2, ...]`` syntax for type-based validation.

        ``Only[int]`` -> validates ``isinstance(value, int)``.
        ``Only[int, str]`` -> validates ``isinstance(value, (int, str))``.

        For value-based whitelists, use the call syntax ``Only("a", "b")``.
        """
        if not isinstance(types, tuple):
            types = (types,)
        if not types:
            raise ValueError("Only[...] requires at least one type")
        for t in types:
            # ``isinstance`` itself only accepts ``type``/``tuple of types``
            # in the second argument; reject anything else up front so
            # the user gets a clear, early error message.
            if not isinstance(t, type):
                raise TypeError(
                    f"Only[...] requires type arguments, got {t!r} "
                    f"of type {type(t).__name__}; "
                    f"use Only(...) for value whitelists"
                )
        instance = cls.__new__(cls)
        instance._allowed = types
        instance._is_type_check = True
        return instance

    # ------------------------------------------------------------------
    # Value / type checking
    # ------------------------------------------------------------------

    def __call__(self, value: Any) -> Any:
        if self._is_type_check:
            if not isinstance(value, self._allowed):
                raise TypeError(
                    f"Value {value!r} is not an instance of any of "
                    f"{self._type_names()!r}"
                )
            return value
        if value not in self._allowed:
            raise ValueError(
                f"Value {value!r} is not one of {self._allowed!r}"
            )
        return value

    def __contains__(self, value: Any) -> bool:
        if self._is_type_check:
            return isinstance(value, self._allowed)
        return value in self._allowed

    # ------------------------------------------------------------------
    # Representation & comparison
    # ------------------------------------------------------------------

    @property
    def allowed(self) -> tuple[Any, ...]:
        """The tuple of allowed values or types (declaration order, deduplicated)."""
        return self._allowed

    @property
    def is_type_check(self) -> bool:
        """``True`` for type whitelists (``Only[int, str]``), ``False`` for value whitelists."""
        return self._is_type_check

    def _type_names(self) -> tuple[str, ...]:
        return tuple(getattr(t, "__name__", repr(t)) for t in self._allowed)

    def __repr__(self) -> str:
        if self._is_type_check:
            return f"Only[{', '.join(self._type_names())}]"
        return f"Only({', '.join(repr(v) for v in self._allowed)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Only):
            return NotImplemented
        return (
            self._is_type_check == other._is_type_check
            and self._allowed == other._allowed
        )

    def __hash__(self) -> int:
        return hash((self._is_type_check, self._allowed))

    # ------------------------------------------------------------------
    # Dataclass integration
    # ------------------------------------------------------------------

    @classmethod
    def validate(cls, instance: Any) -> None:
        """Validate every field of ``instance`` annotated with an :class:`Only`.

        Looks up the ``metadata["type"]`` entry for each dataclass field
        and verifies that fields tagged with an :class:`Only` instance
        contain a valid value (or an instance of the allowed types).

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
            marker = f.metadata.get("type")
            if not isinstance(marker, Only):
                continue
            value = getattr(instance, f.name, _MISSING)
            try:
                marker(value)
            except (TypeError, ValueError) as exc:
                errors.append(
                    f"{type(instance).__name__}.{f.name}: {exc}"
                )
        if errors:
            raise ValueError(
                f"{len(errors)} field(s) failed Only validation: "
                + "; ".join(errors)
            )

    @classmethod
    def iter_fields(
        cls, instance: Any
    ) -> Iterator[tuple[Field[Any], Any]]:
        """Yield ``(field, value)`` pairs for fields annotated with :class:`Only`."""
        if not is_dataclass(instance):
            raise TypeError(f"{type(instance).__name__!s} is not a dataclass")
        for f in fields(instance):
            marker = f.metadata.get("type")
            if isinstance(marker, Only):
                yield f, marker(getattr(instance, f.name))

    @classmethod
    def from_types(cls, *types: type) -> "Only":
        """Convenience constructor equivalent to ``Only[t1, t2, ...]``."""
        if not types:
            raise ValueError("Only.from_types() requires at least one type")
        # ``__class_getitem__`` accepts either a single type or a tuple;
        # passing the tuple directly is always correct and yields the
        # same result as ``Only[t1, t2, ...]``.
        return cls.__class_getitem__(types)

    @classmethod
    def from_iterable(cls, values: Iterable[Any]) -> "Only":
        """Build an :class:`Only` value whitelist from any iterable of allowed values."""
        materialized: Sequence[Any] = tuple(values)
        if not materialized:
            raise ValueError(
                "Only.from_iterable() requires at least one allowed value"
            )
        return cls(*materialized)
