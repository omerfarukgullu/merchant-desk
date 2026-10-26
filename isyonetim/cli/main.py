"""isyonetim CLI kök uygulaması.

Kullanım:
    python -m isyonetim init
    python -m isyonetim project add "Ürün Satışı"
    python -m isyonetim today
    python -m isyonetim weekly-summary
"""

from pathlib import Path
from typing import Optional

import typer

from isyonetim import config
from isyonetim.cli import ecommerce_cmds, meeting_cmds, project_cmds, report_cmds
from isyonetim.cli.common import console
from isyonetim.core import db

app = typer.Typer(
    help="Yerel, tek kullanıcılı iş yönetim sistemi (proje/görev, toplantı, e-ticaret).",
    no_args_is_help=True,
)

app.add_typer(project_cmds.app, name="project")
app.add_typer(meeting_cmds.app, name="meeting")
app.add_typer(ecommerce_cmds.product_app, name="product")
app.add_typer(ecommerce_cmds.channel_app, name="channel")
app.add_typer(ecommerce_cmds.listing_app, name="listing")
app.add_typer(ecommerce_cmds.price_app, name="price")
app.add_typer(ecommerce_cmds.sale_app, name="sale")
app.command("today")(report_cmds.today)
app.command("weekly-summary")(report_cmds.weekly_summary)


@app.callback()
def main(
    ctx: typer.Context,
    db_path: Optional[str] = typer.Option(
        None, "--db", envvar="ISYONETIM_DB_PATH", help="SQLite veritabanı dosya yolu."
    ),
):
    ctx.obj = {"db_path": config.resolve_db_path(db_path)}


@app.command("init")
def init(ctx: typer.Context):
    """Veritabanını (yoksa) oluştur ve tüm migration'ları uygula."""
    path = ctx.obj["db_path"]
    conn = db.connect(path)
    try:
        applied = db.run_migrations(conn)
    finally:
        conn.close()
    if applied:
        console.print(f"[green]Veritabanı hazır:[/green] {path}")
        console.print(f"Uygulanan migration'lar: {', '.join(applied)}")
    else:
        console.print(f"[green]Veritabanı zaten güncel:[/green] {path}")


@app.command("backup")
def backup(ctx: typer.Context, out_dir: Optional[str] = typer.Option(None, "--out-dir")):
    """SQLite dosyasının zaman damgalı bir kopyasını al."""
    path: Path = ctx.obj["db_path"]
    dest_dir = Path(out_dir).expanduser().resolve() if out_dir else None
    try:
        dest = db.backup_database(path, dest_dir)
    except FileNotFoundError:
        console.print(f"[red]Veritabanı bulunamadı:[/red] {path}. Önce 'init' çalıştırın.")
        raise typer.Exit(code=1) from None
    console.print(f"[green]Yedek alındı:[/green] {dest}")


if __name__ == "__main__":
    app()
