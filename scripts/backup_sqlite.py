from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3


source = Path(os.environ.get("SOURCE_DB", "./data/store.db"))
target_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
target_dir.mkdir(parents=True, exist_ok=True)
target = target_dir / f"store-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.db"

with sqlite3.connect(source) as source_conn, sqlite3.connect(target) as target_conn:
    source_conn.backup(target_conn)
    target_conn.execute("PRAGMA integrity_check")

backups = sorted(target_dir.glob("store-*.db"), reverse=True)
for old in backups[7:]:
    old.unlink()
print(f"Created {target}; retained {min(len(backups), 7)} backups")

