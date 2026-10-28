# isyonetim

[English](README.md) | Türkçe

Tek kişilik işletmeler ve küçük ekipler için, tamamen kendi bilgisayarında
çalışan bir iş yönetim sistemi. Hesap açmak, abonelik ödemek ya da internet
bağlantısı gerekmiyor; bütün veri tek bir SQLite dosyasında, kendi diskinizde
duruyor.

Kurulduğunda boş gelir. Örnek müşteri, hazır ürün listesi yok; işletme adını
ve para birimini Ayarlar'dan girip kendi verinizle başlıyorsunuz.

Üç modül aynı veritabanını paylaşıyor:

- **Proje & Görev** — projeler (ya da gelir kolları), aşamalar ve görevler.
  Her görevin önceliği (bugün / bu hafta / birikmiş), son tarihi ve durumu var.
- **Toplantı & Aksiyon** — tedarikçi, müşteri, mali müşavir görüşmeleri ve
  her görüşmeden çıkan aksiyon maddeleri; sorumlu ve son tarihle birlikte.
- **Satış & Fiyat** — ürünler, satış kanalları, kanal bazlı fiyatlar, rakip
  fiyat takibi, satış defteri, ciro ve kâr.

Bunların üstünde takvim (görev son tarihleri, toplantılar ve aksiyonlar bir ay
ızgarasında), günün özetini ve 14 günlük ciro trendini gösteren genel bakış
ekranı, günlük/haftalık rapor, CSV ve Excel dışa aktarımı, yaklaşan toplantı
için Windows bildirimi ve tek komutla yedekleme var.

## Beş kullanım biçimi

Beşi de aynı veritabanını ve aynı veri katmanını kullanıyor:

1. **Panel** — `run_panel.bat` ya da
   `streamlit run isyonetim/dashboard/app.py`. Günlük kullanım; okumanın
   yanı sıra ekleme ve düzenleme de buradan.
2. **CLI** — `python -m isyonetim --help`. Hızlı giriş ve raporlama.
3. **Masaüstü .exe** — `python build_exe.py`. Python kurulu olmayan bir
   bilgisayarda çift tıklayıp çalıştırmak için.
4. **Ağ sunucusu** — `python run_server.py`. Telefon ya da laptoptan aynı
   veriye erişmek için.
5. **Arka plan hatırlatıcı** — `python tray_app.py`. Sistem tepsisinde durup
   toplantı bildirimi gönderen ayrı, hafif bir uygulama.

## Kurulum

Python 3.10 veya üzeri gerekiyor.

```bash
git clone <depo-adresi>
cd isyonetim

python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS / Linux

pip install -r requirements.txt
```

Masaüstü .exe ve tepsi hatırlatıcısı Windows'a özel; onlar için ek paketler
gerekiyor:

```bash
pip install -r requirements-windows.txt
```

Paket olarak kurarsanız `isyonetim` komutu her dizinden çalışır:

```bash
pip install .
isyonetim --help
```

## İlk çalıştırma

```bash
streamlit run isyonetim/dashboard/app.py
```

Windows'ta `run_panel.bat` dosyasına çift tıklamak da aynı işi yapıyor.

Veritabanı yoksa kendisi oluşturur, önce CLI çalıştırmak gerekmez. Panel
açıldığında **Ayarlar** sayfasından işletme adını, para birimini (TL, EUR,
USD, £ ...), varsayılan sorumluyu ve hatırlatma tercihlerini girin. Panel
başlığı ve bütün tutar etiketleri bu ayarlardan besleniyor.

Ayarlar `data/settings.json` dosyasına yazılıyor ve depoya girmiyor; şablonu
`settings.example.json` içinde.

Sunucu dağıtımı ya da tek seferlik çalıştırma için ayar dosyasını ortam
değişkenleriyle ezebilirsiniz — `ISYONETIM_DB_PATH`,
`ISYONETIM_BUSINESS_NAME`, `ISYONETIM_CURRENCY`, `ISYONETIM_OWNER_NAME`,
`ISYONETIM_REMINDER_LEAD_MINUTES`, `ISYONETIM_DIGEST_AFTER_HOUR`,
`ISYONETIM_SERVER_PORT`. Tam liste ve örnekler `.env.example` dosyasında.
Öncelik sırası: ortam değişkeni, sonra `data/settings.json`, sonra varsayılan.

Panelin dolu hâlini görmek isterseniz jenerik örnek veriyi ayrı bir dosyaya
yükleyebilirsiniz:

```bash
python scripts/seed_demo.py --db demo.db
set ISYONETIM_DB_PATH=%CD%\demo.db
streamlit run isyonetim/dashboard/app.py
```

Betik kendiliğinden hiçbir şey silmiyor: hedef veritabanında kayıt varsa
uyarıp çıkıyor, sıfırlamak için `--reset` ve açık onay istiyor.

## CLI kullanımı

```bash
python -m isyonetim init                     # veritabanını kur / migration uygula
python -m isyonetim --help                   # tüm komutlar

python -m isyonetim project add "Ürün Satışı" --goal "Aylık 100 sipariş"
python -m isyonetim project add-phase "Ürün Satışı" "Tedarikçi görüşmeleri"
python -m isyonetim project add-task "Ürün Satışı" "Stok sayımı" -p today
python -m isyonetim project set-task-status 1 completed

python -m isyonetim meeting add "Tedarikçi görüşmesi" --date 2026-11-03 --time 14:30 --type supplier
python -m isyonetim meeting add-action 1 "Teklif iste" --owner "Yönetici" --due 2026-11-10
python -m isyonetim meeting list-actions --open-only

python -m isyonetim product add "Ürün A" --sku URUN-A --cost 450
python -m isyonetim channel add "Pazar Yeri 1"
python -m isyonetim price add "Ürün A" 599 --channel "Pazar Yeri 1"
python -m isyonetim price add "Ürün A" 579 --competitor "Rakip firma"
python -m isyonetim price compare "Ürün A"
python -m isyonetim sale add "Ürün A" "Pazar Yeri 1" --qty 2 --price 599 --date 2026-11-03

python -m isyonetim today                    # günlük özet
python -m isyonetim weekly-summary           # haftalık özet (üç modül birden)
python -m isyonetim project list-tasks --csv gorevler.csv   # her list komutunda --csv var
python -m isyonetim backup                   # zaman damgalı yedek
```

Proje, ürün ve kanalları hem isimle hem id ile gösterebilirsiniz:
`project add-task 1 "Görev"` ile `project add-task "Ürün Satışı" "Görev"`
aynı işi yapıyor.

Veritabanının yerini değiştirmek için `--db <yol>` seçeneği ya da
`ISYONETIM_DB_PATH` ortam değişkeni kullanılıyor. Depodan çalıştırıldığında
varsayılan konum `data/isyonetim.db`.

## Panel

Sadece görüntülemek için değil; proje, görev, toplantı, aksiyon, ürün, fiyat
ve satış eklemek, durum güncellemek için de kullanılıyor. CLI'den tamamen
bağımsız.

Sayfalar sol panelde: Genel Bakış, Takvim, Proje & Görev, Toplantı & Aksiyon,
E-ticaret, Ayarlar. Sol panelin en üstünde hızlı ekle kutusu var — yazıp
Enter'a bastığınız iş, otomatik oluşturulan "Gelen Kutusu" projesine bugünün
görevi olarak düşüyor, sonra düzenleyip taşıyabiliyorsunuz. Altında yaklaşan
ve geciken işlerin özeti, en altta da yenileme ve yedek alma düğmeleri var.

Tema `.streamlit/config.toml` içinde; aydınlık ve karanlık mod ayrı ayrı
ayarlandı. Sağ üstteki ☰ menüsünden Settings → App theme ile Light / Dark /
Use system setting arasında geçilebiliyor.

## Masaüstü uygulaması (.exe)

Paneli tarayıcı çerçevesi olmadan yerel bir pencerede açıyor.

```bash
python desktop_app.py        # paketlemeden, hızlı test
python build_exe.py          # .exe üret (birkaç dakika sürer)
```

Çıktı `dist\IsYonetimSistemi\IsYonetimSistemi.exe`. Exe tek başına taşınamaz;
`dist\IsYonetimSistemi\` klasörünün tamamı birlikte kopyalanmalı. Masaüstü
kısayolu için `create_shortcut.bat`.

Exe modunda veri ve yedekler `%APPDATA%\isyonetim\data\` altında tutuluyor,
çünkü `dist\` klasörünün içeriği her derlemede değişiyor. İkon
`assets/app_icon.ico` dosyasından geliyor (üretim betiği
`assets/generate_icon.py`).

## Uzaktan erişim

Panel ve exe varsayılan olarak yalnızca bu bilgisayardan erişilebiliyor.
Başka bir cihazdan aynı veriye erişmek için bu bilgisayarı sunucu gibi
bırakıp [Tailscale](https://tailscale.com) ile özel bir ağ kurmak gerekiyor;
veri hep bu bilgisayarda kalıyor, internete açılmıyor.

1. Bu bilgisayarda ve diğer cihazda Tailscale'i kurup aynı hesapla girin.
2. Bu bilgisayarda sunucuyu başlatın, açık kalmalı: `run_server.bat`
3. Diğer cihazın tarayıcısından, `tailscale ip` ile bulduğunuz `100.x.x.x`
   adresine portuyla gidin: `http://100.x.x.x:8501`

**Güvenlik notu:** Bu sayfada giriş ya da şifre yok; erişim kontrolü tamamen
Tailscale ağınıza (ya da aynı Wi-Fi'a) kimin dahil olduğuna dayanıyor. Bu
portu router'da asla doğrudan internete yönlendirmeyin. Ağa açma kararı
yalnızca `run_server.py` içinde veriliyor; düz `streamlit run` ya da exe
kendiliğinden ağa açılmıyor.

## Arka plan hatırlatıcı

Sistem tepsisinde çalışan ayrı ve hafif bir uygulama; panel kapalı olsa bile
her dakika veritabanını kontrol ediyor.

Saati girilmiş bir toplantının başlamasına ayarladığınız süreden (varsayılan
15 dakika) az kaldığında bildirim gönderiyor, her toplantı için yalnızca bir
kez. Saat girilmemiş toplantılar için hatırlatma gitmiyor, sadece takvimde
görünüyorlar. Ayrıca her gün belirlediğiniz saatten (varsayılan 08:00) sonraki
ilk kontrolde o günün görev, toplantı ve geciken aksiyon sayısını tek bir
bildirimde özetliyor.

```bash
python tray_app.py           # geliştirmede
python build_tray_exe.py     # .exe üret
```

Çıktı `dist\IsYonetimHatirlatici\IsYonetimHatirlatici.exe`; streamlit ve
pandas içermediği için ana uygulamadan çok daha küçük. Tepsi simgesine sağ
tıklayınca Paneli Aç, Şimdi Kontrol Et ve Çıkış seçenekleri çıkıyor. Windows
açılışında otomatik başlatmak için `create_startup_shortcut.bat`; kaldırmak
için `shell:startup` klasöründen kısayolu silmek yeterli.

Bildirimler her zaman Windows Bildirim Merkezi'nde görünüyor. Köşede balon
olarak da çıkması, Windows'un Odaklanma Yardımcısı ayarlarına bağlı.

## Veri ve gizlilik

Bütün veri `data/isyonetim.db` içinde, kendi diskinizde. Dışarıya hiçbir şey
gönderilmiyor, Streamlit kullanım istatistikleri kapalı. `data/` ve `backups/`
klasörleri `.gitignore` içinde, yani işletme veriniz yanlışlıkla GitHub'a
gitmiyor.

Yedek almak için `python -m isyonetim backup` ya da panelden yedek alma
düğmesi; kopyalar `backups/` altına zaman damgasıyla yazılıyor. Veritabanı WAL
modunda açıldığı için CLI, panel ve hatırlatıcı aynı dosyayı eşzamanlı
kullanabiliyor.

## Geliştirme

```bash
pip install -r requirements-dev.txt

python -m pytest            # testler
python -m ruff check .      # linter
```

Veri katmanı dışarıdan bir `sqlite3.Connection` alıyor; testler bu sayede
diske dokunmadan, bellekteki bir veritabanıyla çalışıyor. Şema değişikliği
için `isyonetim/migrations/` altına sıradaki numarayla yeni bir `.sql` dosyası
eklemek yeterli: açılışta otomatik uygulanıyor, uygulananlar
`schema_migrations` tablosunda tutuluyor.

## Proje yapısı

```
isyonetim/
  config.py              veri/yedek yolları (depo kökü, kullanıcı klasörü, .exe)
  settings.py            işletme adı, para birimi, hatırlatma tercihleri
  core/db.py             bağlantı + migration çalıştırıcı (WAL modu)
  migrations/            sıralı .sql şema dosyaları
  models/                proje/aşama/görev, toplantı/aksiyon, satış veri erişimi
  cli/                   typer komutları (panelden bağımsız)
  reports/               günlük/haftalık hesaplama, CSV + Excel dışa aktarım
  dashboard/app.py       panel: okuma + yazma (CLI'den bağımsız)
  dashboard/theme_css.py ek görsel efektler
tests/                   pytest testleri (veri katmanı, raporlar, ayarlar, CLI)
scripts/seed_demo.py     opsiyonel jenerik örnek veri
assets/app_icon.ico      uygulama ikonu
desktop_app.py           paneli pywebview penceresinde açar
build_exe.py             masaüstü .exe paketleme
tray_app.py              sistem tepsisi + hatırlatıcı
build_tray_exe.py        hatırlatıcıyı ayrı, hafif .exe'ye paketler
run_panel.bat            paneli bu bilgisayarda açar (çift tıkla)
run_server.py / .bat     paneli ağda erişilebilir sunucu olarak başlatır
create_shortcut.*        masaüstü kısayolu
create_startup_shortcut.*  hatırlatıcıyı Windows başlangıcına ekler
.streamlit/config.toml   tema + sunucu varsayılanları
settings.example.json    ayar dosyası şablonu
```

## Lisans

[MIT](LICENSE).
