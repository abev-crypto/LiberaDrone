bl_info = {
    "name": "LiberaDrone",
    "author": "Abe",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "location": "Node Editor > Add menu",
    "description": "Add not enough drone systems to Blender",
    "category": "Animation",
}

# Import registration modules so RegisterBase collects subclasses
# before register/unregister are invoked.
from liberadronecore.reg import checker_reg, ledeffects_reg  # noqa: F401
from liberadronecore.reg.base_reg import RegisterBase


def register():
    RegisterBase.register_all()


def unregister():
    RegisterBase.unregister_all()


if __name__ == "__main__":
    register()
