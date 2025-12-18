# blender_task_runner.py
import os
import json
import time
import uuid
import mimetypes
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# =========================
# 設定
# =========================
GAS_API_URL = "PUT_YOUR_GAS_WEBAPP_URL_HERE"

DROPBOX_ACCESS_TOKEN = "PUT_YOUR_DROPBOX_ACCESS_TOKEN_HERE"

# Dropboxのアップロード先ルート（任意）
DROPBOX_ROOT_DIR = "/"

# タイムアウト
HTTP_TIMEOUT = 60


# =========================
# 共通HTTP
# =========================
def _http_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "BlenderTaskRunner/1.0"}
    if headers:
        h.update(headers)

    req = Request(url, data=data, headers=h, method="POST")
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as res:
            body = res.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTPError {e.code}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"URLError: {e}") from e


# =========================
# GAS API クライアント
# =========================
def gas_list_tasks(status: str = "READY") -> list[dict]:
    """
    status: READY / IN_PROGRESS / DONE など
    """
    r = _http_json(GAS_API_URL, {"action": "list", "status": status})
    if not r.get("ok"):
        raise RuntimeError(f"GAS list failed: {r}")
    return r.get("tasks", [])

def gas_get_task(task_id: str) -> dict:
    r = _http_json(GAS_API_URL, {"action": "get", "task_id": task_id})
    if not r.get("ok"):
        raise RuntimeError(f"GAS get failed: {r}")
    return r["task"]

def gas_start_task(task_id: str, assignee: str) -> dict:
    """
    排他ロックを取って着手状態にする
    """
    lock_token = str(uuid.uuid4())
    r = _http_json(GAS_API_URL, {
        "action": "start",
        "task_id": task_id,
        "assignee": assignee,
        "lock_token": lock_token,
    })
    if not r.get("ok"):
        return r  # ok=false で理由が入る想定
    r["lock_token"] = lock_token
    return r

def gas_complete_task(task_id: str, lock_token: str, output_dropbox_url: str, output_path: str | None = None) -> dict:
    r = _http_json(GAS_API_URL, {
        "action": "complete",
        "task_id": task_id,
        "lock_token": lock_token,
        "output_dropbox_url": output_dropbox_url,
        "output_path": output_path or "",
    })
    return r

def gas_fail_task(task_id: str, lock_token: str, reason: str) -> dict:
    r = _http_json(GAS_API_URL, {
        "action": "fail",
        "task_id": task_id,
        "lock_token": lock_token,
        "reason": reason,
    })
    return r


# =========================
# Dropbox API（標準ライブラリのみ）
# =========================
def dropbox_upload(local_file: str, dropbox_path: str, overwrite: bool = True) -> dict:
    """
    Dropboxへアップロード（/2/files/upload）
    """
    if not os.path.isfile(local_file):
        raise FileNotFoundError(local_file)

    mode = "overwrite" if overwrite else "add"

    with open(local_file, "rb") as f:
        content = f.read()

    args = {
        "path": dropbox_path,
        "mode": mode,
        "autorename": True,
        "mute": False,
        "strict_conflict": False
    }

    req = Request(
        "https://content.dropboxapi.com/2/files/upload",
        data=content,
        method="POST",
        headers={
            "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps(args),
            "User-Agent": "BlenderTaskRunner/1.0",
        },
    )
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as res:
            body = res.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dropbox upload HTTPError {e.code}: {msg}") from e

def dropbox_create_shared_link(dropbox_path: str) -> str:
    """
    共有URL作成（既にあればそれを返す感じにする）
    """
    payload = {
        "path": dropbox_path,
        "settings": {"requested_visibility": "public"}
    }
    req = Request(
        "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "BlenderTaskRunner/1.0",
        },
    )
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as res:
            body = res.read().decode("utf-8", errors="replace")
            return json.loads(body)["url"]
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        # 既存リンクがある場合は list で拾う
        if "shared_link_already_exists" in msg:
            return dropbox_get_existing_shared_link(dropbox_path)
        raise RuntimeError(f"Dropbox share HTTPError {e.code}: {msg}") from e

def dropbox_get_existing_shared_link(dropbox_path: str) -> str:
    payload = {"path": dropbox_path, "direct_only": True}
    req = Request(
        "https://api.dropboxapi.com/2/sharing/list_shared_links",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "BlenderTaskRunner/1.0",
        },
    )
    with urlopen(req, timeout=HTTP_TIMEOUT) as res:
        body = res.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        links = data.get("links", [])
        if not links:
            raise RuntimeError("No existing shared link found.")
        return links[0]["url"]

def normalize_dropbox_share_url(url: str) -> str:
    """
    dl=0 を dl=1 にしてダウンロード直リンク寄りにする（必要なら）
    """
    if "dropbox.com" in url and "dl=" in url:
        return url.replace("dl=0", "dl=1")
    if "dropbox.com" in url and "dl=" not in url:
        return url + ("&dl=1" if "?" in url else "?dl=1")
    return url


# =========================
# 使い方（サンプル）
# =========================
def run_one_task(task_id: str, local_output_file: str, assignee: str = "BlenderUser"):
    """
    1) タスク着手（ロック）
    2) Dropboxへ成果物アップ
    3) 共有URLをSheetへ書き戻し、完了
    """
    start = gas_start_task(task_id, assignee)
    if not start.get("ok"):
        print("[START DENIED]", start)
        return

    lock_token = start["lock_token"]
    print("[START OK]", task_id, "token=", lock_token)

    try:
        # Dropboxアップ先: /MHDrone/<task_id>/<filename>
        filename = os.path.basename(local_output_file)
        dropbox_path = f"{DROPBOX_ROOT_DIR}/{task_id}/{filename}"

        up = dropbox_upload(local_output_file, dropbox_path, overwrite=True)
        print("[UPLOADED]", up.get("path_display", dropbox_path))

        share_url = dropbox_create_shared_link(dropbox_path)
        share_url = normalize_dropbox_share_url(share_url)
        print("[SHARE]", share_url)

        done = gas_complete_task(task_id, lock_token, share_url, output_path=dropbox_path)
        print("[DONE]", done)

    except Exception as e:
        print("[FAILED]", e)
        try:
            gas_fail_task(task_id, lock_token, str(e))
        except Exception as e2:
            print("[FAIL REPORT ERROR]", e2)


# 実行例：
# run_one_task("L03", r"C:\temp\result.blend", assignee="yuya")
