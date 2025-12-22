from __future__ import annotations

import bpy
from bpy.app.handlers import persistent

from liberadronecore.formation import fn_parse


FORMATION_ROOT = "Formation"
_last_linked: bpy.types.Collection | None = None


def _ensure_root(scene: bpy.types.Scene) -> bpy.types.Collection:
    col = bpy.data.collections.get(FORMATION_ROOT)
    if col is None:
        col = bpy.data.collections.new(FORMATION_ROOT)
        scene.collection.children.link(col)
    else:
        try:
            if col.name not in scene.collection.children:
                scene.collection.children.link(col)
        except TypeError:
            scene.collection.children.link(col)
    return col


def _link_collection(scene: bpy.types.Scene, collection: bpy.types.Collection) -> None:
    global _last_linked
    root = _ensure_root(scene)
    if collection is None:
        return

    for child in list(root.children):
        if child != collection:
            root.children.unlink(child)
    if collection.name not in root.children:
        root.children.link(collection)
    _last_linked = collection


@persistent
def update_formation(scene: bpy.types.Scene) -> None:
    schedule = fn_parse.get_cached_schedule()
    if not schedule:
        return

    frame = scene.frame_current
    active = None
    for entry in schedule:
        if entry.start <= frame < entry.end and entry.collection:
            active = entry
    if not active:
        return

    _link_collection(scene, active.collection)


def register():
    if update_formation not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(update_formation)


def unregister():
    if update_formation in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_formation)
