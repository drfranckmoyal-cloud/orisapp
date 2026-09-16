#!/usr/bin/env python3
"""Base PostgreSQL locale pour le développement, sans Docker ni Homebrew.

Utilise les binaires PostgreSQL officiels fournis par le paquet PyPI
`pixeltable-pgserver` (dépendance de dev de services/api). Les données vivent
hors du Bureau iCloud, dans ~/Library/Application Support/Oris/postgres.

Crée le rôle `oris` (mot de passe `oris`, dev uniquement) et les bases `oris`
et `oris_test`, puis écoute sur localhost:5432 — la même DATABASE_URL que
infra/docker/docker-compose.yml.

Usage : services/api/.venv/bin/python scripts/dev_postgres.py start|stop|status
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PORT = 5432
DATA_ROOT = Path.home() / "Library" / "Application Support" / "Oris" / "postgres"
PGDATA = DATA_ROOT / "data"
SOCKET_DIR = DATA_ROOT / "socket"
LOG_FILE = DATA_ROOT / "server.log"
ROLE = "oris"
DATABASES = ("oris", "oris_test")


def bin_dir() -> Path:
    from pixeltable_pgserver import utils

    for version in sorted(utils.POSTGRES_VERSIONS):
        candidate = utils.POSTGRES_VERSIONS[version]
        if (candidate / "postgres").exists():
            return candidate
    sys.exit("Binaires PostgreSQL introuvables dans pixeltable-pgserver.")


def run(*args: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(a) for a in args], check=check, capture_output=True, text=True)


def psql(sql: str, database: str = "postgres") -> str:
    result = run(
        bin_dir() / "psql",
        "-h", SOCKET_DIR, "-p", str(PORT), "-U", "postgres", "-d", database,
        "-tAc", sql,
    )  # fmt: skip
    return result.stdout.strip()


def is_running() -> bool:
    return run(bin_dir() / "pg_ctl", "status", "-D", PGDATA, check=False).returncode == 0


def start() -> None:
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)
    if not (PGDATA / "PG_VERSION").exists():
        run(bin_dir() / "initdb", "-D", PGDATA, "-U", "postgres", "--auth=trust", "-E", "UTF8")
    if not is_running():
        options = f"-p {PORT} -k '{SOCKET_DIR}' -c listen_addresses=localhost"
        run(bin_dir() / "pg_ctl", "start", "-w", "-D", PGDATA, "-l", LOG_FILE, "-o", options)
    if psql(f"SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}'") != "1":
        psql(f"CREATE ROLE {ROLE} LOGIN PASSWORD '{ROLE}'")
    for name in DATABASES:
        if psql(f"SELECT 1 FROM pg_database WHERE datname = '{name}'") != "1":
            psql(f"CREATE DATABASE {name} OWNER {ROLE}")
    print(f"PostgreSQL prêt sur localhost:{PORT} (bases : {', '.join(DATABASES)})")


def stop() -> None:
    if is_running():
        run(bin_dir() / "pg_ctl", "stop", "-w", "-D", PGDATA)
    print("PostgreSQL arrêté")


def status() -> None:
    print("en marche" if is_running() else "arrêté")


if __name__ == "__main__":
    commands = {"start": start, "stop": stop, "status": status}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]]()
