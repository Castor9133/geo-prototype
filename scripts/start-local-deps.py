"""Start bare-metal Redis + Postgres for GEORank on Windows (no Docker).

Postgres binaries are copied to ASCII path C:\\georank-runtime\\pgsql because
pgembed under a Chinese project path cannot resolve share/timezone.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

RUNTIME = Path(os.path.expanduser("~/.georank-runtime"))
ASCII_ROOT = Path(r"C:\georank-runtime")
PGDATA = ASCII_ROOT / "pgdata"
PGSQL = ASCII_ROOT / "pgsql"
REDIS_EXE = next(
    (RUNTIME / "redis7").rglob("redis-server.exe"),
    None,
) if (RUNTIME / "redis7").exists() else None
if REDIS_EXE is None:
    REDIS_EXE = RUNTIME / "redis" / "redis-server.exe"
REPO_PGINSTALL = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / ".venv"
    / "Lib"
    / "site-packages"
    / "pgembed"
    / "pginstall"
)


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.4)
    try:
        sock.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def ensure_redis() -> None:
    if port_open(6379):
        print("redis: already on 6379")
        return
    if not REDIS_EXE.exists():
        raise SystemExit(f"missing {REDIS_EXE}; run scripts/_bootstrap_runtime_deps.py")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    log = RUNTIME / "redis.log"
    flags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        flags |= subprocess.DETACHED_PROCESS
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [str(REDIS_EXE), "--port", "6379"],
        cwd=str(REDIS_EXE.parent),
        stdout=open(log, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    for _ in range(40):
        if port_open(6379):
            print(f"redis: started pid={proc.pid} :6379")
            return
        time.sleep(0.25)
    raise SystemExit("redis failed to bind :6379")


def ensure_pgsql_copy() -> None:
    marker = PGSQL / "bin" / "postgres.exe"
    if marker.exists():
        return
    if not REPO_PGINSTALL.exists():
        raise SystemExit("pgembed not installed; pip install pgembed in backend/.venv")
    ASCII_ROOT.mkdir(parents=True, exist_ok=True)
    if PGSQL.exists():
        shutil.rmtree(PGSQL, ignore_errors=True)
    print(f"copying pgembed binaries -> {PGSQL}")
    shutil.copytree(REPO_PGINSTALL, PGSQL)


def ensure_postgres() -> None:
    ensure_pgsql_copy()
    initdb = PGSQL / "bin" / "initdb.exe"
    pg_ctl = PGSQL / "bin" / "pg_ctl.exe"
    psql = PGSQL / "bin" / "psql.exe"

    if port_open(5432):
        print("postgres: already on 5432")
        return

    env = os.environ.copy()
    for key in ("LANG", "LC_ALL", "LC_CTYPE", "LC_COLLATE", "LC_MESSAGES"):
        env[key] = "C"
    env["TZ"] = "GMT"

    ASCII_ROOT.mkdir(parents=True, exist_ok=True)
    if PGDATA.exists() and not (PGDATA / "PG_VERSION").exists():
        shutil.rmtree(PGDATA, ignore_errors=True)

    if not (PGDATA / "PG_VERSION").exists():
        PGDATA.mkdir(parents=True, exist_ok=True)
        # Prefer UTF8. Requires Postgres binaries on an ASCII path
        # (C:\georank-runtime\pgsql) — Chinese project paths break share/timezone.
        cmd = [
            str(initdb),
            "-D",
            str(PGDATA),
            "--auth=trust",
            "--auth-local=trust",
            "--encoding=UTF8",
            "--locale=C",
            "--lc-messages=C",
            "--lc-monetary=C",
            "--lc-numeric=C",
            "--lc-time=C",
            "-U",
            "postgres",
            "--no-instructions",
        ]
        result = subprocess.run(cmd, env=env, capture_output=True)
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).decode("utf-8", errors="replace")
            raise SystemExit(f"initdb failed:\n{detail}")
        conf = PGDATA / "postgresql.conf"
        conf.write_text(
            conf.read_text(encoding="utf-8", errors="replace")
            + "\nlisten_addresses = '127.0.0.1'\nport = 5432\n",
            encoding="ascii",
            errors="ignore",
        )

    log = ASCII_ROOT / "postgres.log"
    result = subprocess.run(
        [str(pg_ctl), "-D", str(PGDATA), "-l", str(log), "-w", "start"],
        env=env,
        capture_output=True,
    )
    if result.returncode != 0 and not port_open(5432):
        detail = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise SystemExit(f"pg_ctl start failed:\n{detail}")

    for _ in range(40):
        if port_open(5432):
            break
        time.sleep(0.25)
    else:
        raise SystemExit("postgres not listening on 5432")

    user = os.environ.get("POSTGRES_USER", "georank")
    password = os.environ.get("POSTGRES_PASSWORD", "georank")
    dbname = os.environ.get("POSTGRES_DB", "georank")
    for sql in (
        f"CREATE USER {user} WITH PASSWORD '{password}' SUPERUSER",
        f"CREATE DATABASE {dbname} OWNER {user}",
    ):
        subprocess.run(
            [
                str(psql),
                "-h",
                "127.0.0.1",
                "-p",
                "5432",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-c",
                sql,
            ],
            env=env,
            capture_output=True,
        )
    print("postgres: ready 127.0.0.1:5432")


def main() -> None:
    ensure_redis()
    ensure_postgres()
    print("deps ready")


if __name__ == "__main__":
    main()
