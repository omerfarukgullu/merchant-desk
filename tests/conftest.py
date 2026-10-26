"""Testler için paylaşılan fixture'lar.

Veri katmanı (models/) kasıtlı olarak dışarıdan bir sqlite3.Connection
alacak şekilde yazıldı; bu sayede testler diske hiç dokunmadan, bellekteki
bir veritabanı üzerinde çalışabilir.
"""

import os
from pathlib import Path

import pytest

from isyonetim.core import db


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Testler geliştiricinin kendi ISYONETIM_* ortam değişkenlerinden
    etkilenmesin — aksi hâlde sonuç makineye göre değişir."""
    for key in [k for k in os.environ if k.startswith("ISYONETIM_")]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def conn():
    """Migration'ları uygulanmış, bellekte (in-memory) bir veritabanı."""
    connection = db.connect(Path(":memory:"))
    db.run_migrations(connection)
    yield connection
    connection.close()


@pytest.fixture
def db_file(tmp_path):
    """Diskte geçici bir veritabanı yolu (henüz oluşturulmamış)."""
    return tmp_path / "test.db"
