"""Bootstrap Redis 7.x for Windows (RESP3 / HELLO) into ~/.georank-runtime/redis7."""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

REDIS_URL = (
    "https://github.com/redis-windows/redis-windows/releases/download/"
    "7.2.15/Redis-7.2.15-Windows-x64-msys2.zip"
)
RUNTIME = Path(os.path.expanduser("~/.georank-runtime"))
REDIS7 = RUNTIME / "redis7"


def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    exe = next(REDIS7.rglob("redis-server.exe"), None) if REDIS7.exists() else None
    if exe and exe.exists():
        print(f"redis7 already present: {exe}")
        return

    zip_path = RUNTIME / "redis7.zip"
    print(f"downloading {REDIS_URL}")
    urllib.request.urlretrieve(REDIS_URL, zip_path)
    if REDIS7.exists():
        shutil.rmtree(REDIS7, ignore_errors=True)
    REDIS7.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(REDIS7)
    zip_path.unlink(missing_ok=True)
    exe = next(REDIS7.rglob("redis-server.exe"), None)
    if not exe:
        raise SystemExit("redis-server.exe not found after extract")
    print(f"redis7 ready: {exe}")


if __name__ == "__main__":
    main()
