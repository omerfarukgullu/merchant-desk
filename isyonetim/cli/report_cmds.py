"""`isyonetim today` ve `isyonetim weekly-summary` komutları."""

import datetime
from typing import Optional

import typer

from isyonetim import settings as settings_module
from isyonetim.cli.common import (
    ACTION_ITEM_COLUMNS,
    MEETING_COLUMNS,
    TASK_COLUMNS,
    console,
    get_conn,
    maybe_export_csv,
    print_table,
)
from isyonetim.reports.today import build_today_summary
from isyonetim.reports.weekly import build_weekly_summary


def today(ctx: typer.Context):
    """Bugün için: öncelikli/vadesi gelen görevler, bugünkü toplantılar, açık aksiyonlar."""
    conn = get_conn(ctx)
    try:
        summary = build_today_summary(conn)
        console.print(f"[bold]Bugün — {summary['date']}[/bold]")
        print_table("Yapılacak görevler", summary["tasks"], TASK_COLUMNS)
        print_table("Bugünkü toplantılar", summary["meetings_today"], MEETING_COLUMNS)
        print_table("Vadesi bugün olan aksiyonlar", summary["due_today_actions"], ACTION_ITEM_COLUMNS)
        print_table("[!] Süresi geçmiş aksiyonlar", summary["overdue_actions"], ACTION_ITEM_COLUMNS)
    finally:
        conn.close()


def weekly_summary(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, "--since", help="YYYY-MM-DD (varsayılan: 7 gün önce)"),
    until: Optional[str] = typer.Option(None, "--until", help="YYYY-MM-DD (varsayılan: bugün)"),
    csv: Optional[str] = typer.Option(None, "--csv", help="Kanal bazlı satış özetini CSV'ye yaz"),
):
    """Görev/aksiyon/e-ticaret için haftalık gözden geçirme özeti."""
    conn = get_conn(ctx)
    try:
        start = datetime.date.fromisoformat(since) if since else None
        end = datetime.date.fromisoformat(until) if until else None
        s = build_weekly_summary(conn, start, end)

        console.print(f"[bold]Haftalık özet — {s['start']} → {s['end']}[/bold]")
        print_table("Tamamlanan görevler", s["completed_tasks"], TASK_COLUMNS)
        print_table("[!] Geciken görevler", s["overdue_tasks"], TASK_COLUMNS)
        print_table("Devam eden görevler", s["in_progress_tasks"], TASK_COLUMNS)
        print_table("[!] Süresi geçmiş aksiyonlar", s["overdue_actions"], ACTION_ITEM_COLUMNS)

        cfg = settings_module.load_settings()
        profit = (
            cfg.money(s["total_profit"], decimals=2)
            if s["total_profit"] is not None
            else "bilinmiyor (maliyet eksik)"
        )
        console.print(
            f"\n[bold]Satışlar:[/bold] {s['sales_count']} kayıt, "
            f"toplam ciro {cfg.money(s['total_revenue'], decimals=2)}, "
            f"toplam kâr {profit}"
        )
        print_table("Kanal bazlı satış", s["channel_totals"])
        print_table("En çok satan ürünler", s["top_selling_products"])
        print_table("En çok kâr eden ürünler", s["top_profit_products"])

        maybe_export_csv(s["channel_totals"], csv)
    finally:
        conn.close()
