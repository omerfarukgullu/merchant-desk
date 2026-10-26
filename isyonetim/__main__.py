import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Bu import, yukarıdaki yeniden yapılandırmadan SONRA olmalı: aksi hâlde
# Windows konsolunda Türkçe karakterler CLI yüklenirken bozulur.
from isyonetim.cli.main import app  # noqa: E402

if __name__ == "__main__":
    app()
