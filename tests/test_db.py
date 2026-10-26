"""core/db.py: migration çalıştırıcı, yol çözümleme ve yedekleme."""

import sqlite3

import pytest

from isyonetim import config
from isyonetim.core import db


def test_migrations_create_all_tables(conn):
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {
        "projects", "phases", "tasks", "meetings", "action_items",
        "products", "channels", "listings", "price_records", "sale_records",
        "schema_migrations",
    } <= names


def test_migrations_are_idempotent(db_file):
    first = db.init_db(db_file)
    assert first == db_file

    connection = db.connect(db_file)
    try:
        # İkinci çalıştırmada uygulanacak yeni migration olmamalı
        assert db.run_migrations(connection) == []
        applied = db.applied_migrations(connection)
        assert "0001_init.sql" in applied
        assert "0002_meeting_time_and_notify.sql" in applied
    finally:
        connection.close()


def test_connect_honours_db_path_env_var(tmp_path, monkeypatch):
    """connect() argümansız çağrıldığında da ISYONETIM_DB_PATH geçerli olmalı.

    Yoksa tray_app.py ile CLI/panel farklı dosyalara bakar, hatırlatıcı boş
    bir veritabanını izler.
    """
    target = tmp_path / "moved.db"
    monkeypatch.setenv("ISYONETIM_DB_PATH", str(target))

    connection = db.connect()
    try:
        opened = connection.execute("PRAGMA database_list").fetchone()[2]
    finally:
        connection.close()

    assert str(target) == opened
    assert config.resolve_db_path() == target


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                "INSERT INTO tasks (project_id, title) VALUES (?, ?)",
                (999, "olmayan projeye görev"),
            )


def test_backup_database_copies_file(db_file, tmp_path):
    db.init_db(db_file)
    out_dir = tmp_path / "yedekler"

    dest = db.backup_database(db_file, out_dir)

    assert dest.exists()
    assert dest.parent == out_dir
    assert dest.read_bytes() == db_file.read_bytes()


def test_backup_database_raises_when_missing(db_file, tmp_path):
    with pytest.raises(FileNotFoundError):
        db.backup_database(db_file, tmp_path)


def test_source_checkout_keeps_data_in_repo_root():
    """Depo kökünden çalıştırıldığında veri proje köküne yazılmalı."""
    root = config.source_checkout_dir()

    assert root is not None, "testler depo kökünden çalışıyor olmalı"
    assert config.DATA_DIR == root / "data"
    assert config.DEFAULT_DB_PATH == root / "data" / "isyonetim.db"


def test_installed_package_uses_user_data_dir(tmp_path, monkeypatch):
    """Kurulu pakette veri site-packages'a yazılmamalı: güncellemede silinir
    ve çoğu kurulumda salt okunur."""
    fake_site_packages = tmp_path / "site-packages"
    (fake_site_packages / "isyonetim").mkdir(parents=True)
    monkeypatch.setattr(config, "PACKAGE_DIR", fake_site_packages / "isyonetim")

    assert config.source_checkout_dir() is None
    assert config.base_dir() == config.user_data_dir()


def test_user_data_dir_is_absolute_and_named():
    path = config.user_data_dir()

    assert path.is_absolute()
    assert path.name == "isyonetim"
