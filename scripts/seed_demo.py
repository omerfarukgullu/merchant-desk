"""Sistemi tanımak için jenerik örnek veri yükler.

Hiçbir gerçek işletmeye ait bilgi içermez — ürünler "Ürün A/B/C", kanallar
"Kendi Sitem / Pazar Yeri 1" gibi yer tutuculardır. Amaç, panelin dolu
hâlini görüp hangi alanın nereye düştüğünü anlamaktır; sonra veritabanını
sıfırlayıp kendi verinizi girersiniz.

Kullanım:
    python scripts/seed_demo.py                 # boş veritabanına ekler
    python scripts/seed_demo.py --reset         # MEVCUT VERİYİ SİLER, onay ister
    python scripts/seed_demo.py --reset --yes   # onay sormadan siler (betikler için)
    python scripts/seed_demo.py --db demo.db    # ayrı bir dosyaya yükler (önerilen)

Varsayılan olarak hiçbir şeyi silmez: veritabanında zaten kayıt varsa
uyarıp çıkar. Gerçek verinizin üzerine yazmamak için en güvenlisi
`--db demo.db` ile ayrı bir dosyaya yüklemektir.

Not: CLI'nin komut yüzeyine dahil değildir; models katmanını doğrudan
kullanan bağımsız bir betiktir.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from isyonetim import config
from isyonetim.core import db
from isyonetim.models import ecommerce as eco
from isyonetim.models import meeting as mtg
from isyonetim.models import project as proj

TODAY = date.today()

# Örnek veride kullanılan tek "kişi" adı — gerçek bir isim değil.
DEMO_OWNER = "Ben"

COUNT_TABLES = (
    "projects", "phases", "tasks", "meetings", "action_items",
    "products", "channels", "listings", "price_records", "sale_records",
)


def d(delta_days: int) -> str:
    return (TODAY + timedelta(days=delta_days)).isoformat()


def existing_row_count(conn) -> int:
    total = 0
    for table in COUNT_TABLES:
        try:
            total += conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:  # tablo henüz yok -> migration uygulanmamış
            pass
    return total


def seed(conn) -> None:
    # --- 1) Ürün satışı (çevrim içi) -------------------------------------
    p1 = proj.create_project(
        conn,
        "Ürün Satışı",
        description="Kendi sitem ve pazar yerleri üzerinden ürün satışı.",
        goal="Aylık 100 sipariş",
        status="in_progress",
    )
    proj.create_phase(conn, p1.id, "Tedarikçi görüşmeleri", status="completed", order_index=1)
    proj.create_phase(conn, p1.id, "Stok takibi kurulumu", status="in_progress", order_index=2)
    proj.create_phase(conn, p1.id, "Fiyat güncelleme rutini", status="planned", order_index=3)

    proj.create_task(
        conn, p1.id, "Haftalık stok sayımı",
        priority_bucket="today", status="in_progress", due_date=d(0),
    )
    proj.create_task(
        conn, p1.id, "Rakip fiyat karşılaştırması çıkar",
        priority_bucket="today", due_date=d(0),
    )
    proj.create_task(
        conn, p1.id, "Pazar yeri komisyon oranlarını kontrol et",
        priority_bucket="this_week", due_date=d(3),
    )
    proj.create_task(conn, p1.id, "Yeni tedarikçiyle görüş", priority_bucket="backlog")

    # --- 2) Yeni satış kanalı --------------------------------------------
    p2 = proj.create_project(
        conn,
        "Yeni Satış Kanalı",
        description="İkinci bir kanalda talep testi, sonra reklam.",
        goal="İlk 30 günde organik talep testi",
        status="planned",
    )
    proj.create_phase(conn, p2.id, "Ürün/niş araştırması", status="completed", order_index=1)
    proj.create_phase(conn, p2.id, "Mağaza kurulumu", status="in_progress", order_index=2)
    proj.create_phase(conn, p2.id, "İçerik testi", status="planned", order_index=3)
    proj.create_phase(conn, p2.id, "Reklam kampanyası", status="planned", order_index=4)

    proj.create_task(
        conn, p2.id, "Mağaza vitrinini düzenle",
        priority_bucket="today", status="in_progress", due_date=d(0),
    )
    proj.create_task(conn, p2.id, "3 adet tanıtım içeriği hazırla", priority_bucket="this_week", due_date=d(2))
    proj.create_task(conn, p2.id, "Ödeme altyapısını bağla", priority_bucket="backlog")

    # --- 3) Resmi kuruluş işleri -----------------------------------------
    p3 = proj.create_project(
        conn,
        "Resmi Kuruluş İşleri",
        description="Şirket kuruluşu, muhasebe ve vergi/sigorta süreçleri.",
        goal="Kuruluş evraklarını tamamlamak",
        status="planned",
    )
    proj.create_phase(conn, p3.id, "Mali müşavir görüşmesi", status="in_progress", order_index=1)
    proj.create_phase(conn, p3.id, "Evrak hazırlığı", status="planned", order_index=2)

    proj.create_task(
        conn, p3.id, "Mali müşavirle kuruluş adımlarını netleştir",
        priority_bucket="today", due_date=d(0),
    )
    proj.create_task(conn, p3.id, "Masraf kalemlerini listele", priority_bucket="backlog")

    # --- Toplantılar + aksiyonlar -----------------------------------------
    m1 = mtg.create_meeting(
        conn, "Tedarikçi görüşmesi", d(-3), meeting_type="supplier", project_id=p1.id,
        participants=f"{DEMO_OWNER}, Tedarikçi Firma", agenda="Fiyat ve vade görüşmesi",
        decisions="Aylık 50 adet alımda %5 iskonto anlaşıldı.",
    )
    mtg.add_action_item(conn, m1.id, "İskonto sözleşmesini imzala", owner=DEMO_OWNER, due_date=d(2))
    mtg.add_action_item(conn, m1.id, "Yeni fiyat listesini sisteme işle", owner=DEMO_OWNER, due_date=d(-1))

    m2 = mtg.create_meeting(
        conn, "Mali müşavir görüşmesi", d(-1), meeting_type="accountant", project_id=p3.id,
        participants=f"{DEMO_OWNER}, Mali Müşavir", agenda="Kuruluş ve vergi süreci",
        decisions="Kuruluş önümüzdeki ay tamamlanacak.",
    )
    mtg.add_action_item(conn, m2.id, "Eksik evrakları hazırla", owner=DEMO_OWNER, due_date=d(0))

    m3 = mtg.create_meeting(
        conn, "Numune değerlendirme toplantısı", d(-5), meeting_type="supplier", project_id=p2.id,
        decisions="Test için 5 ürün numune sipariş edildi.",
    )
    mtg.add_action_item(conn, m3.id, "Numuneleri değerlendir, içerik çek", owner=DEMO_OWNER, due_date=d(3))

    # Yaklaşan, saati girilmiş toplantı — hatırlatıcıyı denemek için
    mtg.create_meeting(
        conn, "Müşteri tanıtım görüşmesi", d(1), meeting_type="customer", project_id=p1.id,
        participants=f"{DEMO_OWNER}, Müşteri", agenda="Ürün tanıtımı", meeting_time="14:30",
    )

    # --- E-ticaret: ürün / kanal / fiyat / satış ---------------------------
    a = eco.create_product(conn, "Ürün A", sku="URUN-A", category="Kategori 1", cost_price=420)
    b = eco.create_product(conn, "Ürün B", sku="URUN-B", category="Kategori 1", cost_price=650)
    c = eco.create_product(conn, "Ürün C", sku="URUN-C", category="Kategori 2", cost_price=180)
    e = eco.create_product(conn, "Ürün D", sku="URUN-D", category="Kategori 2", cost_price=95)

    own_site = eco.create_channel(conn, "Kendi Sitem", channel_type="own_site")
    market1 = eco.create_channel(conn, "Pazar Yeri 1", channel_type="marketplace")
    market2 = eco.create_channel(conn, "Pazar Yeri 2", channel_type="marketplace")
    social = eco.create_channel(conn, "Sosyal Medya", channel_type="social")

    eco.upsert_listing(conn, a.id, own_site.id, price=549)
    eco.upsert_listing(conn, a.id, market1.id, price=559)
    eco.upsert_listing(conn, a.id, market2.id, price=569)
    eco.upsert_listing(conn, b.id, own_site.id, price=799)
    eco.upsert_listing(conn, b.id, market1.id, price=819)
    eco.upsert_listing(conn, c.id, market1.id, price=349)
    eco.upsert_listing(conn, e.id, social.id, price=249)

    # Bir hafta önceki fiyatlar (trend görmek için) + güncel fiyatlar
    eco.add_price_record(conn, a.id, 579, channel_id=market1.id, source="own", recorded_at=d(-7))
    eco.add_price_record(conn, a.id, 599, source="competitor", competitor_name="Rakip 1", recorded_at=d(-7))
    eco.add_price_record(conn, a.id, 559, channel_id=market1.id, source="own")
    eco.add_price_record(conn, a.id, 545, source="competitor", competitor_name="Rakip 1")

    eco.add_price_record(conn, b.id, 799, channel_id=own_site.id, source="own")
    eco.add_price_record(conn, b.id, 779, source="competitor", competitor_name="Rakip 2")

    # Satış defteri (son ~1 hafta)
    eco.add_sale(conn, a.id, market2.id, d(-1), quantity=3, unit_price=569)
    eco.add_sale(conn, a.id, market1.id, d(-3), quantity=5, unit_price=559)
    eco.add_sale(conn, a.id, own_site.id, d(0), quantity=1, unit_price=549)
    eco.add_sale(conn, b.id, own_site.id, d(-2), quantity=2, unit_price=799)
    eco.add_sale(conn, c.id, market1.id, d(-6), quantity=4, unit_price=349)
    eco.add_sale(conn, e.id, social.id, d(-1), quantity=2, unit_price=249, unit_cost=110, note="Kargo dahil maliyet")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jenerik örnek veri yükler (gerçek işletme bilgisi içermez).",
    )
    parser.add_argument(
        "--db", metavar="YOL",
        help="Hedef veritabanı dosyası (varsayılan: normal veritabanı). "
             "Gerçek verinize dokunmamak için ör. --db demo.db kullanın.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Hedef veritabanındaki TÜM kayıtları silip sıfırdan yükler.",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="--reset onayını sormadan kabul et (betikler için).",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve() if args.db else config.resolve_db_path()

    if args.reset and db_path.exists():
        if not args.yes:
            print(f"DİKKAT: Bu işlem şu veritabanını SİLECEK:\n  {db_path}")
            answer = input("Devam etmek için 'sil' yazın: ").strip().lower()
            if answer != "sil":
                print("İptal edildi, hiçbir şey silinmedi.")
                return 1
        db_path.unlink()
        # WAL/SHM artıkları da gitsin, yoksa silinen veri geri gelebilir
        for suffix in ("-wal", "-shm"):
            sidecar = db_path.with_name(db_path.name + suffix)
            if sidecar.exists():
                sidecar.unlink()
        print(f"Silindi: {db_path}")

    conn = db.connect(db_path)
    try:
        db.run_migrations(conn)

        existing = existing_row_count(conn)
        if existing:
            print(
                f"Bu veritabanında zaten {existing} kayıt var:\n  {db_path}\n"
                "Örnek veri eklenmedi (mevcut verinizle karışmasın diye).\n"
                "Seçenekler:\n"
                "  --db demo.db   ayrı bir demo dosyasına yükle (önerilen)\n"
                "  --reset        bu veritabanını sıfırlayıp örnek veriyi yükle"
            )
            return 1

        seed(conn)
    finally:
        conn.close()

    print(f"Örnek veriler yüklendi -> {db_path}")
    if args.db:
        print(f"Bu veriyle çalışmak için:  set ISYONETIM_DB_PATH={db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
