"""SQLite bağlantı yönetimi ve migration çalıştırıcı.

Tasarım kararı: ORM yok. Her modül (models/*.py) kendisine verilen
sqlite3.Connection üzerinde çalışır; bu da modülleri birbirinden
bağımsız, in-memory veritabanı ile kolayca test edilebilir kılar.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from isyonetim import config

_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Veritabanına bağlanır.

    Yol verilmezse resolve_db_path() kullanılır, yani ISYONETIM_DB_PATH de
    dikkate alınır. tray_app.py gibi argümansız çağıranların CLI ve panelle
    aynı dosyayı görmesi buna bağlı.
    """
    path = db_path or config.resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    conn.execute(_MIGRATIONS_TABLE)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def run_migrations(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    """migrations/ altındaki uygulanmamış .sql dosyalarını sıraya göre uygular.

    Uygulanan migration dosya adlarının listesini döner (boşsa zaten güncel).
    """
    directory = migrations_dir or config.MIGRATIONS_DIR
    already_applied = applied_migrations(conn)
    newly_applied = []
    for sql_file in sorted(directory.glob("*.sql")):
        if sql_file.name in already_applied:
            continue
        script = sql_file.read_text(encoding="utf-8")
        with conn:
            conn.executescript(script)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (sql_file.name,),
            )
        newly_applied.append(sql_file.name)
    return newly_applied


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or config.resolve_db_path()
    conn = connect(path)
    try:
        run_migrations(conn)
    finally:
        conn.close()
    return path


def backup_database(db_path: Path, out_dir: Path | None = None) -> Path:
    """SQLite dosyasının zaman damgalı bir kopyasını alır, hedef yolu döner.

    CLI (`isyonetim backup`) ve dashboard'daki "Şimdi yedek al" butonu bunu
    paylaşır — iki yerde ayrı ayrı yazılmasın diye.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {db_path}")
    dest_dir = out_dir or config.BACKUP_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{db_path.stem}_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, dest)
    return dest
