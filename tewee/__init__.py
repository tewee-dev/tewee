"""Tewee module - simplify metadata & dataclass handling, clean & developer-friendly."""

from .api import EmailStr, Only
from .version import __version__, __version_tuple__

__all__ = [
    "EmailStr",
    "Only",
    "__version__",
    "__version_tuple__",
]
