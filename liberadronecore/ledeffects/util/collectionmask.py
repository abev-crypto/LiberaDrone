import bpy


def _unique_collection_name(base: str) -> str:
    if not bpy.data.collections.get(base):
        return base
    idx = 1
    while True:
        name = f"{base}.{idx:03d}"
        if not bpy.data.collections.get(name):
            return name
        idx += 1
