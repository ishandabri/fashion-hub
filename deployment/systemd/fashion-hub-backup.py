#!/usr/bin/env python3
"""Create and retain verified SQLite backups for the Fashion Hub systemd job."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BACKUP_ROOT = Path(os.environ.get("BACKUP_ROOT", "/mnt/WebAppsBkp/fashion-hub"))
STAGING_ROOT = Path(os.environ.get("STAGING_ROOT", "/var/lib/fashion-hub-backup"))
SOURCE_DB_VALUE = os.environ.get("SOURCE_DB", "")
SOURCE_DB = Path(SOURCE_DB_VALUE) if SOURCE_DB_VALUE else None
RETENTION_COUNT = int(os.environ.get("RETENTION_COUNT", "3"))
LOCK_PATH = Path(os.environ.get("LOCK_FILE", "/run/lock/fashion-hub-backup.lock"))


def fail(message: str) -> "NoReturn":
    print(f"fashion-hub-backup: ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if SOURCE_DB is None:
        fail("SOURCE_DB is required")
    if not SOURCE_DB.is_file():
        fail(f"source database does not exist: {SOURCE_DB}")
    if RETENTION_COUNT < 1:
        fail("RETENTION_COUNT must be positive")

    mount_root = BACKUP_ROOT.parent
    if not mount_root.is_mount():
        fail(f"backup mount is unavailable: {mount_root}")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOCK_PATH.open("w") as lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("fashion-hub-backup: another backup run is already active")
            return

        backup_date = datetime.now().strftime("%Y-%m-%d")
        final_dir = BACKUP_ROOT / backup_date
        remote_staging_dir = BACKUP_ROOT / f".{backup_date}.partial.{os.getpid()}"
        remote_previous_dir = BACKUP_ROOT / f".{backup_date}.previous.{os.getpid()}"
        local_staging_dir = STAGING_ROOT / f".{backup_date}.partial.{os.getpid()}"
        backup_file = local_staging_dir / "backup.db"
        shutil.rmtree(local_staging_dir, ignore_errors=True)
        shutil.rmtree(remote_staging_dir, ignore_errors=True)
        shutil.rmtree(remote_previous_dir, ignore_errors=True)
        local_staging_dir.mkdir()

        try:
            with sqlite3.connect(SOURCE_DB) as source, sqlite3.connect(backup_file) as target:
                source.backup(target)
                result = target.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0].lower() != "ok":
                    fail(f"integrity check failed: {result}")

            checksum = sha256(backup_file)
            (local_staging_dir / "SHA256SUMS").write_text(f"{checksum}  backup.db\n", encoding="utf-8")
            (local_staging_dir / "METADATA.txt").write_text(
                f"source={SOURCE_DB}\ncompleted_at={datetime.now().astimezone().isoformat()}\n"
                "format=sqlite-online-backup\nstatus=complete\n",
                encoding="utf-8",
            )
            (local_staging_dir / "COMPLETE").touch()
            remote_staging_dir.mkdir()
            for filename in ("backup.db", "SHA256SUMS", "METADATA.txt", "COMPLETE"):
                shutil.copy2(local_staging_dir / filename, remote_staging_dir / filename)
            if final_dir.exists():
                final_dir.rename(remote_previous_dir)
            remote_staging_dir.rename(final_dir)
            shutil.rmtree(remote_previous_dir, ignore_errors=True)
        except Exception:
            shutil.rmtree(local_staging_dir, ignore_errors=True)
            shutil.rmtree(remote_staging_dir, ignore_errors=True)
            shutil.rmtree(remote_previous_dir, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(local_staging_dir, ignore_errors=True)

        complete_dirs = sorted(
            (path for path in BACKUP_ROOT.iterdir() if path.is_dir() and DATE_PATTERN.match(path.name) and (path / "COMPLETE").is_file()),
            key=lambda path: path.name,
            reverse=True,
        )
        for old_dir in complete_dirs[RETENTION_COUNT:]:
            print(f"fashion-hub-backup: pruning {old_dir}")
            shutil.rmtree(old_dir)
        print(f"fashion-hub-backup: complete: {final_dir}")


if __name__ == "__main__":
    main()
