"""Arka planda çalışan toplantı/görev hatırlatıcısı (sistem tepsisi).

pystray ile küçük bir simge gösterir; arka planda periyodik olarak
veritabanını kontrol edip başlamasına az kalmış (saati girilmiş) toplantılar
için Windows bildirimi gönderir, günde bir kez de "bugün ne var" özetini
bildirir.

CLI'den ve dashboard'dan bağımsız, ayrı ve hafif bir süreçtir - Streamlit/
pywebview başlatmaz, sadece isyonetim.models ve isyonetim.reports katmanını
okur (aynı SQLite dosyasını, WAL modu sayesinde CLI/dashboard ile eşzamanlı
kullanabilir).

Çalıştırma (geliştirme, arka planda sürekli açık kalır):
    .venv\\Scripts\\python.exe tray_app.py

.exe paketleme:
    .venv\\Scripts\\python.exe build_tray_exe.py

Windows başlangıcına otomatik eklemek için:
    create_startup_shortcut.bat
"""

import json
import subprocess
import sys
import threading
from datetime import date, datetime
from pathlib import Path

import pystray
from PIL import Image
from winotify import Notification, audio

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from isyonetim import config
from isyonetim import settings as settings_module
from isyonetim.core import db
from isyonetim.models import meeting as meeting_model
from isyonetim.reports.today import build_today_summary, format_today_digest

APP_ID = "isyonetim"
CHECK_INTERVAL_SECONDS = 60

# İşletme adı, hatırlatma süresi ve günlük özet saati Ayarlar'dan
# (data/settings.json veya ISYONETIM_* ortam değişkenleri) okunur; her
# kontrolde yeniden okunur, böylece ayar değişince hatırlatıcıyı yeniden
# başlatmak gerekmez.

STATE_PATH = config.BASE_DIR / "tray_state.json"

_stop_event = threading.Event()
_icon: pystray.Icon | None = None


def _icon_image() -> Image.Image:
    if getattr(sys, "frozen", False):
        path = Path(sys._MEIPASS) / "app_icon.ico"  # noqa: SLF001
    else:
        path = Path(__file__).resolve().parent / "assets" / "app_icon.ico"
    return Image.open(path)


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")


def app_title() -> str:
    return settings_module.load_settings().panel_title


def notify(title: str, msg: str, sound=audio.Reminder) -> None:
    n = Notification(app_id=APP_ID, title=title, msg=msg, duration="long")
    n.set_audio(sound, loop=False)
    n.show()


def check_meeting_reminders() -> int:
    """Başlamasına az kalmış toplantılar için bildirim gönderir. Kaç tane
    gönderildiğini döner."""
    conn = db.connect()
    try:
        now = datetime.now()
        today_s = now.date().isoformat()
        now_hhmm = now.strftime("%H:%M")
        due = meeting_model.list_meetings_needing_reminder(
            conn, today_s, now_hhmm,
            lead_minutes=settings_module.load_settings().reminder_lead_minutes,
        )
        for m in due:
            notify(
                f"Toplantı yaklaşıyor — {m.meeting_time}",
                m.title,
            )
            meeting_model.mark_reminder_sent(conn, m.id)
        return len(due)
    finally:
        conn.close()


def check_daily_digest(force: bool = False) -> bool:
    """Bugün için ilk kez (ya da force=True ile her zaman) 'bugün ne var'
    özetini bildirir. Gönderildiyse True döner."""
    state = _load_state()
    today_s = date.today().isoformat()
    if not force:
        if state.get("last_digest_date") == today_s:
            return False
        if datetime.now().hour < settings_module.load_settings().digest_after_hour:
            return False

    conn = db.connect()
    try:
        summary = build_today_summary(conn)
    finally:
        conn.close()

    msg = format_today_digest(summary)
    notify("Günlük özet", msg, sound=audio.Default)
    state["last_digest_date"] = today_s
    _save_state(state)
    return True


def check_now(force_digest: bool = False) -> None:
    check_meeting_reminders()
    check_daily_digest(force=force_digest)


def _background_loop() -> None:
    while not _stop_event.is_set():
        try:
            check_now()
        except Exception as exc:  # arka plan döngüsü asla sessizce ölmemeli
            notify(f"{app_title()} — hata", f"Kontrol sırasında hata: {exc}", sound=audio.Silent)
        _stop_event.wait(CHECK_INTERVAL_SECONDS)


def _open_app(_icon=None, _item=None) -> None:
    if getattr(sys, "frozen", False):
        # build_exe.py ve build_tray_exe.py çıktıları dist\ altında kardeş
        # klasörlerdir (dist\IsYonetimSistemi\, dist\IsYonetimHatirlatici\);
        # ikisi de yerinde durduğu sürece elle dosya kopyalamaya gerek yok.
        tray_dir = Path(sys.executable).resolve().parent
        exe = tray_dir.parent / "IsYonetimSistemi" / "IsYonetimSistemi.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
        else:
            notify(
                app_title(),
                f"Panel bulunamadı: {exe}. dist\\IsYonetimSistemi\\ klasörü "
                "dist\\IsYonetimHatirlatici\\ ile aynı üst klasörde olmalı.",
                sound=audio.Silent,
            )
        return
    base_dir = Path(__file__).resolve().parent
    subprocess.Popen(
        [sys.executable, str(base_dir / "desktop_app.py")],
        cwd=str(base_dir),
    )


def _check_now_action(_icon=None, _item=None) -> None:
    check_now(force_digest=True)


def _quit_action(icon: pystray.Icon, _item=None) -> None:
    _stop_event.set()
    icon.stop()


def main() -> None:
    global _icon

    conn = db.connect()
    try:
        db.run_migrations(conn)  # tray app CLI/dashboard hiç çalıştırılmadan da açılabilsin diye
    finally:
        conn.close()

    threading.Thread(target=_background_loop, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("Paneli Aç", _open_app, default=True),
        pystray.MenuItem("Şimdi Kontrol Et", _check_now_action),
        pystray.MenuItem("Çıkış", _quit_action),
    )
    _icon = pystray.Icon(APP_ID, _icon_image(), app_title(), menu)
    _icon.run()


if __name__ == "__main__":
    main()
