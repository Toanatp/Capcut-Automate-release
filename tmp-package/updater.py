import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import List
import hashlib
import re

from archive_utils import safe_extract_zip


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capto Desktop Updater")
    parser.add_argument("--zip", dest="zip_path", required=True, help="Path to downloaded update zip")
    parser.add_argument("--target", dest="target_dir", required=True, help="App install directory")
    parser.add_argument("--pid", dest="wait_pid", type=int, default=0, help="PID of app process to wait for exit")
    parser.add_argument("--restart-cmd", dest="restart_cmd", default="", help="JSON array command to restart app")
    parser.add_argument("--expected-sha256", dest="expected_sha256", default="", help="Expected SHA256 of update zip")
    parser.add_argument("--cleanup-zip", action="store_true", help="Delete update zip after applying")
    return parser.parse_args(argv or [])


def _calculate_file_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower()


def _is_pid_running(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        if os.name == "nt":
            creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}"],
                capture_output=True,
                text=True,
                creationflags=creation_flags,
            )
            output = str(result.stdout or "")
            if "No tasks are running" in output:
                return False
            return str(pid) in output
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _wait_for_pid_exit(pid: int, timeout_seconds: int = 240) -> bool:
    if not pid or pid <= 0:
        return True
    end_at = time.time() + max(5, int(timeout_seconds))
    while time.time() < end_at:
        if not _is_pid_running(pid):
            return True
        time.sleep(0.25)
    return not _is_pid_running(pid)


def _resolve_extracted_root(staging_dir: str) -> str:
    try:
        entries = [name for name in os.listdir(staging_dir) if name not in {".", "..", "__MACOSX"}]
    except Exception:
        entries = []
    if len(entries) == 1:
        single_path = os.path.join(staging_dir, entries[0])
        if os.path.isdir(single_path):
            return single_path
    return staging_dir


def _copy_tree_overwrite(source_dir: str, target_dir: str) -> None:
    os.makedirs(target_dir, exist_ok=True)
    for name in os.listdir(source_dir):
        src = os.path.join(source_dir, name)
        dst = os.path.join(target_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def _start_restart_command(restart_cmd_raw: str, target_dir: str) -> int:
    restart_cmd: List[str] = []
    if restart_cmd_raw:
        try:
            parsed = json.loads(restart_cmd_raw)
            if isinstance(parsed, list):
                restart_cmd = [str(x) for x in parsed if str(x or "").strip()]
            elif isinstance(parsed, str) and parsed.strip():
                restart_cmd = [parsed.strip()]
        except Exception:
            pass
    if not restart_cmd:
        return 0
    try:
        creation_flags = 0
        if os.name == "nt":
            creation_flags = int(getattr(subprocess, "DETACHED_PROCESS", 0)) | int(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        subprocess.Popen(
            restart_cmd,
            cwd=target_dir,
            creationflags=creation_flags,
            close_fds=bool(os.name != "nt"),
        )
        return 0
    except Exception as exc:
        print(f"Updater restart error: {exc}")
        return 5


def run_update(args: argparse.Namespace) -> int:
    zip_path = str(getattr(args, "zip_path", "") or "").strip()
    target_dir = str(getattr(args, "target_dir", "") or "").strip()
    wait_pid = int(getattr(args, "wait_pid", 0) or 0)
    restart_cmd_raw = str(getattr(args, "restart_cmd", "") or "").strip()
    expected_sha256 = str(getattr(args, "expected_sha256", "") or "").strip().lower()
    cleanup_zip = bool(getattr(args, "cleanup_zip", False))

    if not zip_path or not os.path.isfile(zip_path):
        print("Updater error: missing update archive.")
        return 2
    if not target_dir:
        print("Updater error: missing target directory.")
        return 3
    if expected_sha256:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            print("Updater error: invalid expected SHA256 value.")
            return 6
        actual_sha256 = _calculate_file_sha256(zip_path)
        if actual_sha256 != expected_sha256:
            print(
                f"Updater error: package checksum mismatch. expected={expected_sha256} actual={actual_sha256}"
            )
            return 6

    target_dir = os.path.abspath(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    _wait_for_pid_exit(wait_pid, timeout_seconds=240)

    staging_dir = tempfile.mkdtemp(prefix="capto-update-stage-")
    try:
        safe_extract_zip(zip_path, staging_dir)
        source_root = _resolve_extracted_root(staging_dir)
        _copy_tree_overwrite(source_root, target_dir)
    except Exception as exc:
        print(f"Updater error: {exc}")
        return 4
    finally:
        try:
            shutil.rmtree(staging_dir, ignore_errors=True)
        except Exception:
            pass

    if cleanup_zip:
        try:
            os.remove(zip_path)
        except Exception:
            pass

    return _start_restart_command(restart_cmd_raw, target_dir)


if __name__ == "__main__":
    sys.exit(run_update(_parse_args(sys.argv[1:])))
