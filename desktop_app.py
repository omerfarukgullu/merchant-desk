"""Masaüstü uygulaması giriş noktası.

Streamlit dashboard'unu (isyonetim/dashboard/app.py) arka planda başlatır ve
pywebview ile tarayıcı çerçevesi olmadan yerel bir pencerede açar.

Geliştirmede çalıştırma:
    .venv\\Scripts\\python.exe desktop_app.py

.exe paketleme:
    .venv\\Scripts\\python.exe build_exe.py
"""

import os
import sys
from pathlib import Path

from streamlit_desktop_app import start_desktop_app

from isyonetim import settings as settings_module


def _dashboard_script_path() -> str:
    if getattr(sys, "frozen", False):
        # build_exe.py, streamlit'in dosyadan çalıştırabilmesi için
        # isyonetim/dashboard/app.py'yi bundle köküne ham veri dosyası
        # olarak da ekler (modül olarak import edilebilir olması yetmez).
        return str(Path(sys._MEIPASS) / "app.py")  # noqa: SLF001
    return str(Path(__file__).resolve().parent / "isyonetim" / "dashboard" / "app.py")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # Streamlit .streamlit/config.toml'u (tema dahil) çalışma dizinine
        # göre bulur. build_exe.py bu klasörü bundle köküne kopyalar; burada
        # da çalışma dizinini oraya taşıyoruz ki tema, kısayoldan/çift
        # tıklamayla nereden başlatılırsa başlatılsın her zaman uygulansın.
        os.chdir(sys._MEIPASS)  # noqa: SLF001

    app_title = settings_module.load_settings().panel_title
    start_desktop_app(_dashboard_script_path(), title=app_title, width=1280, height=860)
