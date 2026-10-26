"""Yol ve varsayılan ayar sabitleri.

Veritabanı konumu ISYONETIM_DB_PATH ortam değişkeni veya CLI'nin --db
seçeneği ile geçersiz kılınabilir; hiçbiri verilmezse DEFAULT_DB_PATH
kullanılır.

Veri klasörü çalıştırma biçimine göre değişir. Depodan çalıştırıldığında
proje köküne bağlı data/ ve backups/ kullanılır. pip ile kurulmuş pakette
ya da PyInstaller .exe'sinde buna yazmak olmaz (biri site-packages, diğeri
her açılışta silinen geçici klasör), o yüzden kullanıcıya özel kalıcı bir
klasöre düşülür.
"""

import os
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = PACKAGE_DIR / "migrations"

IS_FROZEN = bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """İşletim sistemine uygun, kullanıcıya özel kalıcı veri klasörü."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "isyonetim"


def source_checkout_dir() -> Path | None:
    """Depo kökünden çalıştırılıyorsa depo kökünü, değilse None döner.

    Ayırt edici işaret paketin üst klasöründeki pyproject.toml / .git;
    site-packages'ta bunlar bulunmaz.
    """
    candidate = PACKAGE_DIR.parent
    for marker in ("pyproject.toml", ".git"):
        if (candidate / marker).exists():
            return candidate
    return None


def base_dir() -> Path:
    if IS_FROZEN:
        return user_data_dir()
    return source_checkout_dir() or user_data_dir()


BASE_DIR = base_dir()

DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"

DEFAULT_DB_PATH = DATA_DIR / "isyonetim.db"

# İşletmeye özel ayarlar (işletme adı, para birimi...). Kullanıcı verisiyle
# birlikte data/ altında tutulur; isyonetim/settings.py okur/yazar.
SETTINGS_PATH = DATA_DIR / "settings.json"


def resolve_db_path(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env_value = os.environ.get("ISYONETIM_DB_PATH")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_DB_PATH
