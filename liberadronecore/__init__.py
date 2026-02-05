bl_info = {
    "name": "LiberaDrone",
    "author": "Yuya Abe",
    "version": (1, 3, 3),
    "blender": (4, 3, 0),
    "location": "Node Editor > Add menu",
    "description": "Add not enough drone to Blender",
    "category": "Animation",
}

_MISSING_PACKAGES: list[str] = []
_REGISTERED_FULL = False
_REGISTERED_FALLBACK = False


def _check_required_packages() -> list[str]:
    from liberadronecore.system import request as _request
    missing = _request.deps_missing()
    return [pip_name for pip_name, _import_name in missing]


_MISSING_PACKAGES = _check_required_packages()

def register():
    global _REGISTERED_FULL, _REGISTERED_FALLBACK
    if _MISSING_PACKAGES:
        from liberadronecore.system import update as _update
        from liberadronecore.operators import update as _update_ops
        from liberadronecore.ui import addon_pref as _addon_pref
        _update.register()
        _update_ops.UpdateOps.register()
        _addon_pref.register()
        _REGISTERED_FALLBACK = True
        return

    import liberadronecore.reg
    import liberadronecore.formation
    import liberadronecore.ledeffects
    import liberadronecore.operators
    from liberadronecore.reg.base_reg import RegisterBase

    RegisterBase.register_all()
    _REGISTERED_FULL = True


def unregister():
    global _REGISTERED_FULL, _REGISTERED_FALLBACK
    if _REGISTERED_FULL and not _MISSING_PACKAGES:
        from liberadronecore.reg.base_reg import RegisterBase
        RegisterBase.unregister_all()
        _REGISTERED_FULL = False
        return

    if _REGISTERED_FALLBACK:
        from liberadronecore.system import update as _update
        from liberadronecore.operators import update as _update_ops
        from liberadronecore.ui import addon_pref as _addon_pref
        _addon_pref.unregister()
        _update_ops.UpdateOps.unregister()
        _update.unregister()
        _REGISTERED_FALLBACK = False
