"""İşletmeye özel ayarlar: işletme adı, para birimi, hatırlatma tercihleri.

İşletme adı ve para birimi koda gömülü değil; her kullanıcı kendi değerini
verir. Öncelik sırası: ortam değişkeni (ISYONETIM_CURRENCY gibi), sonra
data/settings.json, sonra buradaki varsayılanlar.

Dosya yoksa ya da bozuksa varsayılanlara düşülür; ayar okumak uygulamayı
hiçbir durumda çökertmez.
"""

import json
import os
from dataclasses import asdict, dataclass, fields

from isyonetim import config

DEFAULT_BUSINESS_NAME = "İşletmem"
DEFAULT_CURRENCY = "TL"
DEFAULT_REMINDER_LEAD_MINUTES = 15
DEFAULT_DIGEST_AFTER_HOUR = 8
DEFAULT_SERVER_PORT = 8501


@dataclass
class Settings:
    """Tek bir işletmenin yapılandırması."""

    business_name: str = DEFAULT_BUSINESS_NAME
    currency: str = DEFAULT_CURRENCY
    owner_name: str = ""
    reminder_lead_minutes: int = DEFAULT_REMINDER_LEAD_MINUTES
    digest_after_hour: int = DEFAULT_DIGEST_AFTER_HOUR
    server_port: int = DEFAULT_SERVER_PORT

    @property
    def panel_title(self) -> str:
        """Dashboard başlığı / masaüstü pencere adı."""
        return f"{self.business_name} — İş Yönetim Paneli"

    def money(self, amount: float | None, decimals: int = 0) -> str:
        """Tutarı para birimiyle birlikte biçimlendirir; None -> '—'."""
        if amount is None:
            return "—"
        return f"{amount:,.{decimals}f} {self.currency}"

    def money_label(self, base: str) -> str:
        """'Bu hafta ciro' -> 'Bu hafta ciro (TL)' gibi etiketler üretir."""
        return f"{base} ({self.currency})"


# Ortam değişkeni adı -> alan adı
_ENV_PREFIX = "ISYONETIM_"
_INT_FIELDS = {"reminder_lead_minutes", "digest_after_hour", "server_port"}


def _from_file() -> dict:
    path = config.SETTINGS_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _from_env() -> dict:
    values = {}
    for f in fields(Settings):
        raw = os.environ.get(f"{_ENV_PREFIX}{f.name.upper()}")
        if raw is None or raw == "":
            continue
        values[f.name] = raw
    return values


def _coerce(values: dict) -> dict:
    """Bilinmeyen anahtarları atar, sayısal alanları int'e çevirir."""
    known = {f.name for f in fields(Settings)}
    clean = {}
    for key, value in values.items():
        if key not in known:
            continue
        if key in _INT_FIELDS:
            try:
                clean[key] = int(value)
            except (TypeError, ValueError):
                continue  # bozuk değer -> varsayılan kalsın
        else:
            clean[key] = str(value)
    return clean


def load_settings() -> Settings:
    """Ayarları dosya ve ortam değişkenlerini birleştirerek okur.

    Önbelleklenmez; Ayarlar sayfasındaki değişiklik bir sonraki yüklemede
    görünsün, uygulamayı yeniden başlatmak gerekmesin diye.
    """
    merged = {**_coerce(_from_file()), **_coerce(_from_env())}
    return Settings(**merged)


def save_settings(settings: Settings) -> None:
    """Ayarları data/settings.json dosyasına yazar.

    Ortam değişkeni verilmişse dosyadaki değeri ezmeye devam eder; panel bu
    durumu ilgili alanın yanında belirtir.
    """
    path = config.SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def env_overrides() -> set[str]:
    """Ortam değişkeniyle sabitlenmiş (dosyadan değiştirilemeyen) alan adları."""
    return set(_coerce(_from_env()).keys())
