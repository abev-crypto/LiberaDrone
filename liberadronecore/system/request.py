import sys, subprocess, importlib, ensurepip

REQUIRED = [
    # (pip_name, import_name, version_suffix)
    ("numpy", "numpy", None),
    # ("scipy", "scipy", "==1.11.4"),
    # ("Pillow", "PIL", None),
]

def deps_missing():
    missing = []
    for pip_name, import_name, _ver in REQUIRED:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append((pip_name, import_name))
    return missing

def pip_install(pip_name, version_suffix=None):
    try:
        ensurepip.bootstrap()
    except Exception:
        pass

    pkg = pip_name + (version_suffix or "")
    cmd = [sys.executable, "-m", "pip", "install", pkg, "--upgrade"]
    subprocess.check_call(cmd)