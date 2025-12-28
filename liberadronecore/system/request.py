import sys, subprocess, importlib, ensurepip
import bpy
import os
import site
from pathlib import Path

REQUIRED = [
    # (pip_name, import_name, version_suffix)
    ("numpy", "numpy", None),
    ("scipy", "scipy", None),
    ("Pillow", "PIL", None),
    ("opencv-python", "cv2", None),
    ("PySide6", "PySide6", None),
    ("matplotlib", "matplotlib", None),
]

def deps_missing():
    missing = []
    for pip_name, import_name, _ver in REQUIRED:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append((pip_name, import_name))
    return missing

def find_blender_python_exe() -> str:
    # 1) sys.prefix から探す（かなり確実）
    # 例: .../Blender/4.x/python
    prefix = Path(sys.prefix)

    candidates = [
        prefix / "bin" / "python.exe",     # Windowsの典型
        prefix / "bin" / "python3.exe",
        prefix / "python.exe",             # 念のため
    ]
    for p in candidates:
        if p.exists():
            return str(p)

    # 2) blender.exe の場所から推測して探す（保険）
    blender_exe = Path(bpy.app.binary_path)
    root = blender_exe.parent
    # よくある配置: <root>/python/bin/python.exe
    candidates = list(root.glob("**/python.exe"))
    for p in candidates:
        # なるべく python/bin/python.exe を優先したい
        if p.name.lower() == "python.exe" and ("\\python\\bin\\" in str(p).lower() or "/python/bin/" in str(p).lower()):
            return str(p)

    raise RuntimeError("Blender同梱の python.exe を見つけられませんでした。")

def pip_install(pip_name: str, version_suffix: str | None = None):
    bpy.ops.wm.console_toggle()
    py = find_blender_python_exe()

    addon_dir = Path(__file__).resolve().parent
    prefix_dir = addon_dir / "deps"
    prefix_dir.mkdir(exist_ok=True)

    pkg = pip_name + (version_suffix or "")

    # まず pip を用意（Blender同梱Python側で）
    subprocess.check_call([py, "-m", "ensurepip", "--upgrade"])

    subprocess.check_call([
        py, "-m", "pip", "install",
        "--upgrade",
        "--prefix", str(prefix_dir),
        pkg
    ])

    # import 可能にする
    site_packages = (
        prefix_dir / "Lib" / "site-packages"
    )
    if site_packages.exists():
        sp = str(site_packages)
        if sp not in sys.path:
            sys.path.insert(0, sp)
