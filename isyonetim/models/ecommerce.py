"""Product / Channel / Listing / PriceRecord / SaleRecord veri erişim katmanı."""

import sqlite3
from dataclasses import dataclass
from datetime import date

CHANNEL_TYPES = ("own_site", "marketplace", "social", "other")
LISTING_STATUSES = ("active", "inactive", "out_of_stock")
PRICE_SOURCES = ("own", "competitor")


@dataclass
class Product:
    id: int
    name: str
    sku: str | None
    category: str | None
    cost_price: float | None
    created_at: str
    updated_at: str


@dataclass
class Channel:
    id: int
    name: str
    channel_type: str
    created_at: str


@dataclass
class Listing:
    id: int
    product_id: int
    channel_id: int
    price: float | None
    status: str
    updated_at: str


@dataclass
class PriceRecord:
    id: int
    product_id: int
    channel_id: int | None
    source: str
    competitor_name: str | None
    price: float
    recorded_at: str
    note: str | None


@dataclass
class SaleRecord:
    id: int
    product_id: int
    channel_id: int
    sale_date: str
    quantity: int
    unit_price: float
    unit_cost: float | None
    note: str | None
    created_at: str


def _product(row: sqlite3.Row) -> Product:
    return Product(**dict(row))


def _channel(row: sqlite3.Row) -> Channel:
    return Channel(**dict(row))


def _listing(row: sqlite3.Row) -> Listing:
    return Listing(**dict(row))


def _price_record(row: sqlite3.Row) -> PriceRecord:
    return PriceRecord(**dict(row))


def _sale_record(row: sqlite3.Row) -> SaleRecord:
    return SaleRecord(**dict(row))


# ---- Product -----------------------------------------------------------

def create_product(
    conn: sqlite3.Connection,
    name: str,
    sku: str | None = None,
    category: str | None = None,
    cost_price: float | None = None,
) -> Product:
    with conn:
        cur = conn.execute(
            "INSERT INTO products (name, sku, category, cost_price) VALUES (?, ?, ?, ?)",
            (name, sku, category, cost_price),
        )
    return get_product(conn, cur.lastrowid)


def get_product(conn: sqlite3.Connection, product_id: int) -> Product | None:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _product(row) if row else None


def get_product_by_name(conn: sqlite3.Connection, name: str) -> Product | None:
    row = conn.execute("SELECT * FROM products WHERE name = ?", (name,)).fetchone()
    return _product(row) if row else None


def list_products(conn: sqlite3.Connection, category: str | None = None) -> list[Product]:
    if category:
        rows = conn.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY name", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    return [_product(r) for r in rows]


def update_product_cost(conn: sqlite3.Connection, product_id: int, cost_price: float) -> None:
    with conn:
        conn.execute(
            "UPDATE products SET cost_price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cost_price, product_id),
        )


# ---- Channel -------------------------------------------------------------

def create_channel(
    conn: sqlite3.Connection, name: str, channel_type: str = "marketplace"
) -> Channel:
    with conn:
        cur = conn.execute(
            "INSERT INTO channels (name, channel_type) VALUES (?, ?)", (name, channel_type)
        )
    return get_channel(conn, cur.lastrowid)


def get_channel(conn: sqlite3.Connection, channel_id: int) -> Channel | None:
    row = conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()
    return _channel(row) if row else None


def get_channel_by_name(conn: sqlite3.Connection, name: str) -> Channel | None:
    row = conn.execute("SELECT * FROM channels WHERE name = ?", (name,)).fetchone()
    return _channel(row) if row else None


def list_channels(conn: sqlite3.Connection) -> list[Channel]:
    rows = conn.execute("SELECT * FROM channels ORDER BY name").fetchall()
    return [_channel(r) for r in rows]


# ---- Listing (ürünün bir kanaldaki güncel durumu) -------------------------

def upsert_listing(
    conn: sqlite3.Connection,
    product_id: int,
    channel_id: int,
    price: float | None = None,
    status: str = "active",
) -> Listing:
    with conn:
        conn.execute(
            """INSERT INTO listings (product_id, channel_id, price, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (product_id, channel_id)
               DO UPDATE SET price = excluded.price, status = excluded.status,
                              updated_at = CURRENT_TIMESTAMP""",
            (product_id, channel_id, price, status),
        )
    row = conn.execute(
        "SELECT * FROM listings WHERE product_id = ? AND channel_id = ?",
        (product_id, channel_id),
    ).fetchone()
    return _listing(row)


def list_listings(
    conn: sqlite3.Connection,
    product_id: int | None = None,
    channel_id: int | None = None,
) -> list[Listing]:
    clauses = []
    params: list = []
    if product_id is not None:
        clauses.append("product_id = ?")
        params.append(product_id)
    if channel_id is not None:
        clauses.append("channel_id = ?")
        params.append(channel_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM listings {where} ORDER BY product_id, channel_id", params
    ).fetchall()
    return [_listing(r) for r in rows]


# ---- PriceRecord (kendi fiyatım / rakip fiyatı, zaman damgalı) ------------

def add_price_record(
    conn: sqlite3.Connection,
    product_id: int,
    price: float,
    channel_id: int | None = None,
    source: str = "own",
    competitor_name: str | None = None,
    note: str | None = None,
    recorded_at: str | date | None = None,
) -> PriceRecord:
    ts = recorded_at.isoformat() if isinstance(recorded_at, date) else recorded_at
    with conn:
        if ts is not None:
            cur = conn.execute(
                """INSERT INTO price_records
                       (product_id, channel_id, source, competitor_name, price, recorded_at, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (product_id, channel_id, source, competitor_name, price, ts, note),
            )
        else:
            cur = conn.execute(
                """INSERT INTO price_records
                       (product_id, channel_id, source, competitor_name, price, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (product_id, channel_id, source, competitor_name, price, note),
            )
    row = conn.execute("SELECT * FROM price_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _price_record(row)


def list_price_records(
    conn: sqlite3.Connection,
    product_id: int | None = None,
    channel_id: int | None = None,
    source: str | None = None,
    since: str | date | None = None,
) -> list[PriceRecord]:
    clauses = []
    params: list = []
    if product_id is not None:
        clauses.append("product_id = ?")
        params.append(product_id)
    if channel_id is not None:
        clauses.append("channel_id = ?")
        params.append(channel_id)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if since is not None:
        s = since.isoformat() if isinstance(since, date) else since
        clauses.append("recorded_at >= ?")
        params.append(s)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM price_records {where} ORDER BY recorded_at DESC, id DESC", params
    ).fetchall()
    return [_price_record(r) for r in rows]


def latest_price_comparison(conn: sqlite3.Connection, product_id: int) -> dict:
    """Bir ürün için en güncel kendi fiyatlarım(kanal bazlı) ve rakip fiyatlarını döner."""
    own_rows = conn.execute(
        """SELECT pr.channel_id, c.name AS channel_name, pr.price, pr.recorded_at
           FROM price_records pr
           JOIN channels c ON c.id = pr.channel_id
           WHERE pr.product_id = ? AND pr.source = 'own'
             AND pr.id IN (
                 SELECT MAX(id) FROM price_records
                 WHERE product_id = ? AND source = 'own'
                 GROUP BY channel_id
             )""",
        (product_id, product_id),
    ).fetchall()
    competitor_rows = conn.execute(
        """SELECT pr.competitor_name, pr.price, pr.recorded_at
           FROM price_records pr
           WHERE pr.product_id = ? AND pr.source = 'competitor'
             AND pr.id IN (
                 SELECT MAX(id) FROM price_records
                 WHERE product_id = ? AND source = 'competitor'
                 GROUP BY competitor_name
             )""",
        (product_id, product_id),
    ).fetchall()
    return {
        "own": [dict(r) for r in own_rows],
        "competitors": [dict(r) for r in competitor_rows],
    }


# ---- SaleRecord ------------------------------------------------------------

def add_sale(
    conn: sqlite3.Connection,
    product_id: int,
    channel_id: int,
    sale_date: str | date,
    quantity: int,
    unit_price: float,
    unit_cost: float | None = None,
    note: str | None = None,
) -> SaleRecord:
    sdate = sale_date.isoformat() if isinstance(sale_date, date) else sale_date
    with conn:
        cur = conn.execute(
            """INSERT INTO sale_records
                   (product_id, channel_id, sale_date, quantity, unit_price, unit_cost, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (product_id, channel_id, sdate, quantity, unit_price, unit_cost, note),
        )
    row = conn.execute("SELECT * FROM sale_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _sale_record(row)


def list_sales(
    conn: sqlite3.Connection,
    since: str | date | None = None,
    until: str | date | None = None,
    product_id: int | None = None,
    channel_id: int | None = None,
) -> list[SaleRecord]:
    clauses = []
    params: list = []
    if since is not None:
        s = since.isoformat() if isinstance(since, date) else since
        clauses.append("sale_date >= ?")
        params.append(s)
    if until is not None:
        u = until.isoformat() if isinstance(until, date) else until
        clauses.append("sale_date <= ?")
        params.append(u)
    if product_id is not None:
        clauses.append("product_id = ?")
        params.append(product_id)
    if channel_id is not None:
        clauses.append("channel_id = ?")
        params.append(channel_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM sale_records {where} ORDER BY sale_date DESC, id DESC", params
    ).fetchall()
    return [_sale_record(r) for r in rows]


def sale_profit(sale: SaleRecord, fallback_cost: float | None = None) -> float | None:
    """Bir satışın toplam kârını hesaplar; maliyet yoksa None döner."""
    cost = sale.unit_cost if sale.unit_cost is not None else fallback_cost
    if cost is None:
        return None
    return round((sale.unit_price - cost) * sale.quantity, 2)
