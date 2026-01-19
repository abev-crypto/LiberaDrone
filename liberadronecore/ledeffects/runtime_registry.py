from __future__ import annotations

from typing import Callable, Dict, Optional

_RUNTIME_FUNCTIONS: Dict[str, Callable] = {}


def register_runtime_function(func: Optional[Callable] = None, *, name: Optional[str] = None):
    if func is None:
        def decorator(target):
            register_runtime_function(target, name=name)
            return target
        return decorator
    fn_name = name or getattr(func, "__name__", None)
    if not fn_name:
        return func
    _RUNTIME_FUNCTIONS[fn_name] = func
    return func


def register_runtime_functions(funcs: Dict[str, Callable]) -> None:
    for key, func in (funcs or {}).items():
        if callable(func):
            _RUNTIME_FUNCTIONS[key] = func


def clear_runtime_functions() -> None:
    _RUNTIME_FUNCTIONS.clear()


def runtime_functions() -> Dict[str, Callable]:
    return dict(_RUNTIME_FUNCTIONS)
