#!/usr/bin/env python3
"""Verify the newest complete Fashion Hub SQLite backup."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
from pathlib import Path

BACKUP_ROOT = Path(os.environ.get("BACKUP_ROOT", "/mnt/WebAppsBkp/fashion-hub"))
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main() -> None:
    candidates = sorted(
        (path for path in BACKUP_ROOT.iterdir() if path.is_dir() and DATE_PATTERN.match(path.name) and (path / "COMPLETE").is_file()),
        key=lambda path: path.name,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("fashion-hub-restore-verify: no complete backup found")
    latest = candidates[0]
    backup_file = latest / "backup.db"
    checksum_file = latest / "SHA256SUMS"
    if not backup_file.is_file() or not checksum_file.is_file():
        raise SystemExit(f"fashion-hub-restore-verify: incomplete backup: {latest}")
    expected = checksum_file.read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(backup_file.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"fashion-hub-restore-verify: checksum mismatch: {backup_file}")
    with tempfile.NamedTemporaryFile(suffix=".db") as restored:
        restored_path = Path(restored.name)
        restored.close()
        restored_path.write_bytes(backup_file.read_bytes())
        with sqlite3.connect(restored_path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0].lower() != "ok":
                raise SystemExit(f"fashion-hub-restore-verify: integrity check failed: {result}")
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
    print(f"fashion-hub-restore-verify: verified: {latest}")


if __name__ == "__main__":
    main()
