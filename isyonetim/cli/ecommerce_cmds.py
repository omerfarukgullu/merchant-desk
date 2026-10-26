"""`isyonetim product|channel|listing|price|sale ...` komutları."""

from typing import Optional

import typer

from isyonetim.cli.common import (
    CHANNEL_COLUMNS,
    LISTING_COLUMNS,
    PRICE_RECORD_COLUMNS,
    PRODUCT_COLUMNS,
    SALE_RECORD_COLUMNS,
    console,
    err_console,
    get_conn,
    maybe_export_csv,
    print_table,
)
from isyonetim.models import ecommerce as eco_model

product_app = typer.Typer(help="Ürün yönetimi.")
channel_app = typer.Typer(help="Satış kanalı yönetimi (kendi siteniz, pazar yerleri, sosyal medya...).")
listing_app = typer.Typer(help="Ürünün kanaldaki listeleme durumu ve güncel fiyatı.")
price_app = typer.Typer(help="Fiyat kayıtları (kendi fiyatım + rakip fiyatları).")
sale_app = typer.Typer(help="Satış / sipariş defteri.")


def _resolve_product_id(conn, identifier: str) -> int:
    if identifier.isdigit():
        p = eco_model.get_product(conn, int(identifier))
        if p:
            return p.id
    p = eco_model.get_product_by_name(conn, identifier)
    if p:
        return p.id
    err_console.print(f"Ürün bulunamadı: {identifier!r}")
    raise typer.Exit(code=1)


def _resolve_channel_id(conn, identifier: str) -> int:
    if identifier.isdigit():
        c = eco_model.get_channel(conn, int(identifier))
        if c:
            return c.id
    c = eco_model.get_channel_by_name(conn, identifier)
    if c:
        return c.id
    err_console.print(f"Kanal bulunamadı: {identifier!r}")
    raise typer.Exit(code=1)


# ---- product ---------------------------------------------------------------

@product_app.command("add")
def add_product(
    ctx: typer.Context,
    name: str,
    sku: Optional[str] = typer.Option(None, "--sku"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    cost: Optional[float] = typer.Option(None, "--cost", help="Birim maliyet"),
):
    """Yeni ürün ekle."""
    conn = get_conn(ctx)
    try:
        p = eco_model.create_product(conn, name, sku, category, cost)
        console.print(f"[green]Ürün eklendi:[/green] #{p.id} {p.name}")
    finally:
        conn.close()


@product_app.command("list")
def list_products(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Ürünleri listele."""
    conn = get_conn(ctx)
    try:
        rows = eco_model.list_products(conn, category)
        print_table("Ürünler", rows, PRODUCT_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


# ---- channel -----------------------------------------------------------

@channel_app.command("add")
def add_channel(
    ctx: typer.Context,
    name: str,
    type: str = typer.Option("marketplace", "--type", "-t", help="own_site/marketplace/social/other"),
):
    """Yeni satış kanalı ekle."""
    conn = get_conn(ctx)
    try:
        c = eco_model.create_channel(conn, name, type)
        console.print(f"[green]Kanal eklendi:[/green] #{c.id} {c.name}")
    finally:
        conn.close()


@channel_app.command("list")
def list_channels(ctx: typer.Context, csv: Optional[str] = typer.Option(None, "--csv")):
    """Kanalları listele."""
    conn = get_conn(ctx)
    try:
        rows = eco_model.list_channels(conn)
        print_table("Kanallar", rows, CHANNEL_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


# ---- listing -----------------------------------------------------------

@listing_app.command("set")
def set_listing(
    ctx: typer.Context,
    product: str,
    channel: str,
    price: Optional[float] = typer.Option(None, "--price"),
    status: str = typer.Option("active", "--status", "-s", help="active/inactive/out_of_stock"),
):
    """Ürünün bir kanaldaki listeleme fiyatını/durumunu güncelle (yoksa oluşturur)."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product)
        channel_id = _resolve_channel_id(conn, channel)
        listing = eco_model.upsert_listing(conn, product_id, channel_id, price, status)
        console.print(
            f"[green]Listeleme güncellendi:[/green] ürün #{listing.product_id} "
            f"kanal #{listing.channel_id} -> {listing.price} ({listing.status})"
        )
    finally:
        conn.close()


@listing_app.command("list")
def list_listings_cmd(
    ctx: typer.Context,
    product: Optional[str] = typer.Option(None, "--product"),
    channel: Optional[str] = typer.Option(None, "--channel"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Listelemeleri göster."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product) if product else None
        channel_id = _resolve_channel_id(conn, channel) if channel else None
        rows = eco_model.list_listings(conn, product_id, channel_id)
        print_table("Listelemeler", rows, LISTING_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


# ---- price ---------------------------------------------------------------

@price_app.command("add")
def add_price(
    ctx: typer.Context,
    product: str,
    price: float,
    channel: Optional[str] = typer.Option(None, "--channel", help="Kendi fiyatım için zorunlu"),
    competitor: Optional[str] = typer.Option(None, "--competitor", help="Rakip fiyatı için (rakip firma/mağaza adı)"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Fiyat kaydı ekle: kendi fiyatım (--channel) ya da rakip fiyatı (--competitor)."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product)
        if competitor:
            rec = eco_model.add_price_record(
                conn, product_id, price, source="competitor", competitor_name=competitor, note=note
            )
        elif channel:
            channel_id = _resolve_channel_id(conn, channel)
            rec = eco_model.add_price_record(
                conn, product_id, price, channel_id=channel_id, source="own", note=note
            )
        else:
            err_console.print("Ya --channel (kendi fiyatım) ya da --competitor (rakip) belirtmelisiniz.")
            raise typer.Exit(code=1)
        console.print(f"[green]Fiyat kaydı eklendi:[/green] #{rec.id} {rec.price} ({rec.source})")
    finally:
        conn.close()


@price_app.command("list")
def list_prices(
    ctx: typer.Context,
    product: Optional[str] = typer.Option(None, "--product"),
    source: Optional[str] = typer.Option(None, "--source", help="own/competitor"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Fiyat kayıtlarını listele (en yeni önce)."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product) if product else None
        rows = eco_model.list_price_records(conn, product_id, source=source)
        print_table("Fiyat Kayıtları", rows, PRICE_RECORD_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@price_app.command("compare")
def compare_prices(ctx: typer.Context, product: str):
    """Bir ürün için en güncel kendi fiyatlarımı ve rakip fiyatlarını karşılaştır."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product)
        result = eco_model.latest_price_comparison(conn, product_id)
        console.print(f"[bold]Fiyat karşılaştırması — ürün #{product_id}[/bold]")
        print_table("Kendi fiyatlarım", result["own"])
        print_table("Rakip fiyatları", result["competitors"])
    finally:
        conn.close()


# ---- sale ------------------------------------------------------------------

@sale_app.command("add")
def add_sale(
    ctx: typer.Context,
    product: str,
    channel: str,
    quantity: int = typer.Option(1, "--qty", "-q"),
    unit_price: float = typer.Option(..., "--price"),
    date: str = typer.Option(..., "--date", help="YYYY-MM-DD"),
    unit_cost: Optional[float] = typer.Option(None, "--cost", help="Bu satışa özel maliyet (verilmezse ürünün maliyeti kullanılır)"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Satış kaydı ekle."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product)
        channel_id = _resolve_channel_id(conn, channel)
        sale = eco_model.add_sale(
            conn, product_id, channel_id, date, quantity, unit_price, unit_cost, note
        )
        console.print(f"[green]Satış eklendi:[/green] #{sale.id} {sale.quantity} adet @ {sale.unit_price}")
    finally:
        conn.close()


@sale_app.command("list")
def list_sales_cmd(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, "--since", help="YYYY-MM-DD"),
    until: Optional[str] = typer.Option(None, "--until", help="YYYY-MM-DD"),
    product: Optional[str] = typer.Option(None, "--product"),
    channel: Optional[str] = typer.Option(None, "--channel"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Satışları listele (en yeni önce)."""
    conn = get_conn(ctx)
    try:
        product_id = _resolve_product_id(conn, product) if product else None
        channel_id = _resolve_channel_id(conn, channel) if channel else None
        rows = eco_model.list_sales(conn, since, until, product_id, channel_id)
        print_table("Satışlar", rows, SALE_RECORD_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()
