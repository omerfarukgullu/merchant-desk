"""isyonetim masaüstü uygulamasını .exe'ye paketler (PyInstaller).

Çalıştırma:
    .venv\\Scripts\\python.exe build_exe.py

Çıktı: dist\\IsYonetimSistemi\\IsYonetimSistemi.exe (klasörle birlikte;
klasörün tamamı taşınmalı/kopyalanmalıdır).
"""

import os
from pathlib import Path

import PyInstaller.__main__

REPO_ROOT = Path(__file__).resolve().parent
APP_NAME = "IsYonetimSistemi"


def add_data(src: Path, dest: str) -> str:
    return f"{src}{os.pathsep}{dest}"


def main() -> None:
    icon_path = REPO_ROOT / "assets" / "app_icon.ico"

    args = [
        str(REPO_ROOT / "desktop_app.py"),
        "--name", APP_NAME,
        "--noconfirm",
        "--windowed",
        "--icon", str(icon_path),
        "--paths", str(REPO_ROOT),
        "--collect-all", "streamlit",
        "--copy-metadata", "streamlit",
        "--collect-submodules", "isyonetim",
        "--add-data", add_data(REPO_ROOT / "isyonetim" / "dashboard" / "app.py", "."),
        "--add-data", add_data(REPO_ROOT / "isyonetim" / "migrations", str(Path("isyonetim") / "migrations")),
        "--add-data", add_data(REPO_ROOT / ".streamlit", ".streamlit"),
    ]
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
