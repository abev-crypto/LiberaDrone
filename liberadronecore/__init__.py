bl_info = {
    "name": "LiberaDrone",
    "author": "Abe",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "location": "Node Editor > Add menu",
    "description": "Add not enough drone systems to Blender",
    "category": "Animation",
}

import liberadronecore.reg
import liberadronecore.formation

from liberadronecore.reg.base_reg import RegisterBase

def register():
    RegisterBase.register_all()


def unregister():
    RegisterBase.unregister_all()