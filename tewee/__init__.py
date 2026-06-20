"""Tewee module - simplify metadata & dataclass handling, clean & developer-friendly."""

from .api import  EmailStr
from .version import __version__, __version_tuple__

__all__ = [
    "EmailStr",
    "__version__",
    "__version_tuple__",
]
