"""Dashboard'u AĞ ÜZERİNDEN erişilebilir bir sunucu olarak başlatır.

Masaüstü .exe'den (desktop_app.py) farkı: o sadece bu bilgisayarda, tek bir
pencerede çalışır. Bu betik ise dashboard'u 0.0.0.0'da dinletir; aynı ağdaki
(veya Tailscale ile bağlı) başka bir bilgisayar/telefon, tarayıcıdan bu
bilgisayarın IP'sine giderek aynı veriye erişip okuma/yazma yapabilir.

Ağa açma kararı *sadece burada* verilir: `.streamlit/config.toml` güvenli
varsayılanda (yalnız localhost) kalır, bu betik ise adres/port değerlerini
komut satırı parametresiyle geçersiz kılar. Böylece düz `streamlit run` ya
da masaüstü .exe hiçbir zaman kendiliğinden ağa açılmaz.

Kullanım (bu bilgisayar "sunucu" olacak, açık kalmalı):
    .venv\\Scripts\\python.exe run_server.py

Port, Ayarlar sayfasından (data/settings.json) ya da ISYONETIM_SERVER_PORT
ortam değişkeninden gelir; varsayılan 8501.

Uzaktan (telefon/laptop) erişim için Tailscale kurun (tailscale.com, ücretsiz):
    - Bu bilgisayarda ve diğer cihazda Tailscale'i kurup aynı hesapla girin.
    - Bu bilgisayarda "tailscale ip" komutuyla veya Tailscale simgesinden
      100.x.x.x ile başlayan adresi bulun.
    - Diğer cihazın tarayıcısından http://<o-adres>:<port> adresine gidin.

GÜVENLİK NOTU: Bu sayfada giriş/şifre yoktur — erişim kontrolü tamamen
Tailscale ağınıza (ya da aynı Wi-Fi'a) kimin dahil olduğuna dayanır. Bu
portu asla doğrudan internete (router'da port yönlendirme ile) açmayın.
"""

import socket
import sys
from pathlib import Path

from streamlit.web import cli as stcli

from isyonetim import settings as settings_module

DASHBOARD = Path(__file__).resolve().parent / "isyonetim" / "dashboard" / "app.py"


def local_ips() -> list[str]:
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    return sorted(ips)


def main() -> None:
    port = settings_module.load_settings().server_port

    print("=" * 60)
    print("isyonetim - ağ sunucu modu")
    print("=" * 60)
    ips = local_ips()
    if ips:
        print("Bu ağdaki (ör. aynı Wi-Fi) cihazlardan erişim:")
        for ip in ips:
            print(f"  http://{ip}:{port}")
    print("Tailscale ile uzaktan erişim: 'tailscale ip' ile bulacağınız")
    print(f"100.x.x.x adresiyle  http://<o-adres>:{port}")
    print("Bu sayfada şifre YOKTUR - portu internete yönlendirmeyin.")
    print("Durdurmak için bu pencerede Ctrl+C.")
    print("=" * 60)

    sys.argv = [
        "streamlit", "run", str(DASHBOARD),
        "--server.address=0.0.0.0",
        f"--server.port={port}",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
