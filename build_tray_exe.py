"""tray_app.py'yi .exe'ye paketler (PyInstaller).

Ana masaüstü uygulamasından (build_exe.py) bağımsız, ayrı bir exe'dir —
streamlit/pandas gerekmez, bu yüzden çok daha küçüktür ve hızlı açılır.

Çalıştırma:
    .venv\\Scripts\\python.exe build_tray_exe.py

Çıktı: dist\\IsYonetimHatirlatici\\IsYonetimHatirlatici.exe. Bu klasör,
dist\\IsYonetimSistemi\\ ile aynı üst klasörde (dist\\) kardeş olarak durur;
"İş Yönetim Panelini Aç" menüsü bu ilişkiye göre otomatik bulur, elle
kopyalama gerekmez — ikisini de dist\\ altında olduğu gibi bırakın.
"""

import os
from pathlib import Path

import PyInstaller.__main__

REPO_ROOT = Path(__file__).resolve().parent
APP_NAME = "IsYonetimHatirlatici"


def add_data(src: Path, dest: str) -> str:
    return f"{src}{os.pathsep}{dest}"


def main() -> None:
    icon_path = REPO_ROOT / "assets" / "app_icon.ico"

    args = [
        str(REPO_ROOT / "tray_app.py"),
        "--name", APP_NAME,
        "--noconfirm",
        "--windowed",
        "--icon", str(icon_path),
        "--paths", str(REPO_ROOT),
        "--collect-submodules", "isyonetim.core",
        "--collect-submodules", "isyonetim.models",
        "--collect-submodules", "isyonetim.reports",
        "--hidden-import", "isyonetim.config",
        "--add-data", add_data(icon_path, "."),
        "--add-data", add_data(REPO_ROOT / "isyonetim" / "migrations", str(Path("isyonetim") / "migrations")),
    ]
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
