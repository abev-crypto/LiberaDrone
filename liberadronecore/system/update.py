# updater_github_main.py
# GitHub main ブランチを参照してアドオンをセルフアップデートする簡易実装

from __future__ import annotations

import ast
import io
import os
import re
import shutil
import tempfile
import zipfile
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

import bpy


# -----------------------------
# 設定（Preferences から上書きする想定）
# -----------------------------

@dataclass
class GithubRepo:
    owner: str = "abev-crypto"
    repo: str = "LiberaDrone"
    branch: str = "main"
    # リポジトリ内でアドオンが置かれている相対パス（repo 直下なら空でOK）
    # 例: "src/my_addon" の場合は "src/my_addon"
    addon_subdir: str = "liberadronecore"


# -----------------------------
# ユーティリティ
# -----------------------------

def _http_get_text(url: str, timeout: float = 10.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BlenderAddonUpdater/1.0",
            "Accept": "text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data.decode("utf-8", errors="replace")


def _http_get_bytes(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BlenderAddonUpdater/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_bl_info_version_from_init_py(py_text: str) -> Optional[Tuple[int, int, int]]:
    """
    __init__.py の bl_info = {... "version": (x,y,z) ... } を安全に読む（ast で解析）
    """
    try:
        tree = ast.parse(py_text)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "bl_info":
                    # bl_info の dict literal を期待
                    if isinstance(node.value, (ast.Dict,)):
                        try:
                            d = ast.literal_eval(node.value)
                        except Exception:
                            return None
                        v = d.get("version")
                        if (
                            isinstance(v, tuple)
                            and len(v) >= 2
                            and all(isinstance(i, int) for i in v[:3])
                        ):
                            if len(v) == 2:
                                return (v[0], v[1], 0)
                            return (v[0], v[1], v[2])
    return None


def _version_gt(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> bool:
    return a > b


def _addon_root_dir_from_module(module_name: str) -> str:
    """
    bpy.context.preferences.addons[module].module のルートパスを引く
    """
    mod = __import__(module_name)
    # package の __file__ は __init__.py を指す
    p = os.path.dirname(os.path.abspath(mod.__file__))
    return p


def _safe_rmtree(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


def _copytree_overwrite(src: str, dst: str) -> None:
    """
    dst を消してから src を丸ごとコピー（最もトラブルが少ない）
    """
    tmp_old = dst + ".old"
    # 既存を退避
    if os.path.exists(dst):
        _safe_rmtree(tmp_old)
        os.rename(dst, tmp_old)

    try:
        shutil.copytree(src, dst)
        _safe_rmtree(tmp_old)
    except Exception:
        # 失敗したら元に戻す
        _safe_rmtree(dst)
        if os.path.exists(tmp_old):
            os.rename(tmp_old, dst)
        raise


# -----------------------------
# メイン処理
# -----------------------------

def get_local_version(module_name: str) -> Optional[Tuple[int, int, int]]:
    mod = __import__(module_name)
    bl_info = getattr(mod, "bl_info", None)
    if isinstance(bl_info, dict):
        v = bl_info.get("version")
        if isinstance(v, tuple) and len(v) >= 2:
            if len(v) == 2:
                return (int(v[0]), int(v[1]), 0)
            return (int(v[0]), int(v[1]), int(v[2]))
    return None


def get_remote_version(repo: GithubRepo) -> Optional[Tuple[int, int, int]]:
    # raw URL: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/__init__.py
    sub = repo.addon_subdir.strip("/")

    init_path = "__init__.py" if not sub else f"{sub}/__init__.py"
    url = f"https://raw.githubusercontent.com/{repo.owner}/{repo.repo}/{repo.branch}/{init_path}"
    text = _http_get_text(url)
    return _parse_bl_info_version_from_init_py(text)


def download_main_zip(repo: GithubRepo) -> bytes:
    # https://github.com/{owner}/{repo}/archive/refs/heads/main.zip
    url = f"https://github.com/{repo.owner}/{repo.repo}/archive/refs/heads/{repo.branch}.zip"
    return _http_get_bytes(url)


def install_from_zip_bytes(zip_bytes: bytes, repo: GithubRepo, target_addon_dir: str) -> None:
    """
    zip を展開して、repo.addon_subdir にあるアドオンディレクトリ内容を target_addon_dir に上書きする
    """
    sub = repo.addon_subdir.strip("/")

    with tempfile.TemporaryDirectory() as td:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        zf.extractall(td)

        # zip の最上位は "{repo}-{branch}/" になるのが通例
        # 例: myrepo-main/
        top_dirs = [d for d in os.listdir(td) if os.path.isdir(os.path.join(td, d))]
        if not top_dirs:
            raise RuntimeError("ZIPの展開先にトップディレクトリが見つかりませんでした。")
        top = os.path.join(td, top_dirs[0])

        src_addon_dir = top if not sub else os.path.join(top, sub)
        if not os.path.isdir(src_addon_dir):
            raise RuntimeError(f"ZIP内に addon_subdir が見つかりません: {src_addon_dir}")

        # src_addon_dir の中身がアドオンとして妥当か最低限チェック
        if not os.path.exists(os.path.join(src_addon_dir, "__init__.py")):
            raise RuntimeError("ZIP内の対象フォルダに __init__.py がありません。addon_subdir 設定を確認してください。")

        # 置換（丸ごと）
        _copytree_overwrite(src_addon_dir, target_addon_dir)


# -----------------------------
# Blender Operator / UI
# -----------------------------

class LD_OT_check_update(bpy.types.Operator):
    bl_idname = "liberadrone.check_update"
    bl_label = "Check Update (GitHub main)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        addon_key = __package__.split(".")[0]
        prefs = context.preferences.addons[addon_key].preferences

        repo = GithubRepo(
            owner=prefs.gh_owner,
            repo=prefs.gh_repo,
            branch=prefs.gh_branch,
            addon_subdir=prefs.gh_addon_subdir,
        )

        try:
            local_v = get_local_version(addon_key)
            remote_v = get_remote_version(repo)
        except Exception as e:
            self.report({'ERROR'}, f"更新チェック失敗: {e}")
            return {'CANCELLED'}

        prefs.last_local_version = str(local_v) if local_v else "None"
        prefs.last_remote_version = str(remote_v) if remote_v else "None"

        if not local_v or not remote_v:
            prefs.update_available = False
            self.report({'WARNING'}, "バージョン取得に失敗（bl_info を確認してください）")
            return {'FINISHED'}

        prefs.update_available = _version_gt(remote_v, local_v)
        if prefs.update_available:
            self.report({'INFO'}, f"更新あり: local {local_v} -> remote {remote_v}")
        else:
            self.report({'INFO'}, f"最新です: {local_v}")
        return {'FINISHED'}


class LD_OT_apply_update(bpy.types.Operator):
    bl_idname = "liberadrone.apply_update"
    bl_label = "Update Now (Download & Install)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        addon_key = __package__.split(".")[0]
        prefs = context.preferences.addons[addon_key].preferences
        repo = GithubRepo(
            owner=prefs.gh_owner,
            repo=prefs.gh_repo,
            branch=prefs.gh_branch,
            addon_subdir=prefs.gh_addon_subdir,
        )

        try:
            addon_dir = _addon_root_dir_from_module(addon_key)
            zip_bytes = download_main_zip(repo)
            install_from_zip_bytes(zip_bytes, repo, addon_dir)

            # ここで再読込を試みることもできるが、自己更新は不安定になりがち。
            # 基本は再起動推奨。
            prefs.update_available = False
            self.report({'INFO'}, "更新をインストールしました。Blenderを再起動してください。")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"更新に失敗: {e}")
            return {'CANCELLED'}

classes = (
    LD_OT_check_update,
    LD_OT_apply_update,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
