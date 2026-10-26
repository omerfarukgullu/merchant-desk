"""CLI komutları arasında paylaşılan yardımcılar (db bağlantısı, tablo yazdırma)."""

import sqlite3
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from isyonetim.core import db

console = Console()
err_console = Console(stderr=True, style="red")


def get_db_path(ctx: typer.Context) -> Path:
    return ctx.obj["db_path"]


def get_conn(ctx: typer.Context) -> sqlite3.Connection:
    return db.connect(get_db_path(ctx))


def print_table(title: str, rows: list[Any], columns: list[str] | None = None) -> None:
    if not rows:
        console.print(f"[dim]{title}: kayıt yok[/dim]")
        return
    import dataclasses

    dict_rows = [dataclasses.asdict(r) if dataclasses.is_dataclass(r) else dict(r) for r in rows]
    cols = columns or list(dict_rows[0].keys())
    table = Table(title=title, header_style="bold cyan")
    for col in cols:
        table.add_column(col)
    for row in dict_rows:
        table.add_row(*("" if row.get(c) is None else str(row.get(c)) for c in cols))
    console.print(table)


PROJECT_COLUMNS = ["id", "name", "status", "goal"]
PHASE_COLUMNS = ["id", "project_id", "name", "status", "order_index"]
TASK_COLUMNS = ["id", "project_id", "phase_id", "title", "status", "priority_bucket", "due_date"]
MEETING_COLUMNS = ["id", "title", "meeting_type", "meeting_date", "meeting_time", "project_id"]
ACTION_ITEM_COLUMNS = ["id", "meeting_id", "task_id", "description", "owner", "due_date", "status"]
PRODUCT_COLUMNS = ["id", "name", "sku", "category", "cost_price"]
CHANNEL_COLUMNS = ["id", "name", "channel_type"]
LISTING_COLUMNS = ["id", "product_id", "channel_id", "price", "status"]
PRICE_RECORD_COLUMNS = ["id", "product_id", "channel_id", "source", "competitor_name", "price", "recorded_at"]
SALE_RECORD_COLUMNS = ["id", "product_id", "channel_id", "sale_date", "quantity", "unit_price", "unit_cost"]


def maybe_export_csv(rows: list[Any], csv_path: str | None) -> None:
    if not csv_path:
        return
    from isyonetim.reports.export import export_rows

    out = export_rows(rows, csv_path)
    console.print(f"[green]CSV yazıldı:[/green] {out}")
