
"""
Base helper to standardize register/unregister routines.
Subclasses are automatically collected so they can be looped over in main.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class RegisterBase(ABC):
    """Base class that tracks subclasses needing register/unregister."""

    _registry: ClassVar[list[type["RegisterBase"]]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is RegisterBase:
            return
        RegisterBase._registry.append(cls)

    @classmethod
    def registered_classes(cls) -> tuple[type["RegisterBase"], ...]:
        """Return collected subclasses in definition order."""
        return tuple(cls._registry)

    @classmethod
    def register_all(cls) -> None:
        """Call register on every collected subclass."""
        for subcls in cls._registry:
            subcls.register()

    @classmethod
    def unregister_all(cls) -> None:
        """Call unregister on every collected subclass in reverse order."""
        for subcls in reversed(cls._registry):
            subcls.unregister()

    @classmethod
    @abstractmethod
    def register(cls) -> None:
        """Register Blender classes or other resources."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def unregister(cls) -> None:
        """Undo the work done by register."""
        raise NotImplementedError
