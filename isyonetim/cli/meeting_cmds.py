"""`isyonetim meeting ...` komutları: Meeting / ActionItem."""

from typing import Optional

import typer

from isyonetim.cli.common import (
    ACTION_ITEM_COLUMNS,
    MEETING_COLUMNS,
    console,
    get_conn,
    maybe_export_csv,
    print_table,
)
from isyonetim.cli.project_cmds import _resolve_project_id
from isyonetim.models import meeting as meeting_model

app = typer.Typer(help="Toplantı/görüşme kayıtları ve aksiyon maddeleri.")


@app.command("add")
def add_meeting(
    ctx: typer.Context,
    title: str,
    date: str = typer.Option(..., "--date", help="YYYY-MM-DD"),
    time: Optional[str] = typer.Option(None, "--time", help="HH:MM (verilirse hatırlatma bu saate göre çalışır)"),
    type: str = typer.Option("other", "--type", "-t", help="supplier/customer/accountant/internal/other"),
    project: Optional[str] = typer.Option(None, "--project"),
    participants: Optional[str] = typer.Option(None, "--participants"),
    agenda: Optional[str] = typer.Option(None, "--agenda"),
    decisions: Optional[str] = typer.Option(None, "--decisions"),
):
    """Yeni toplantı kaydı ekle."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project) if project else None
        m = meeting_model.create_meeting(
            conn, title, date, type, project_id, participants, agenda, decisions, time
        )
        when = f"{m.meeting_date} {m.meeting_time}" if m.meeting_time else m.meeting_date
        console.print(f"[green]Toplantı eklendi:[/green] #{m.id} {m.title} ({when})")
    finally:
        conn.close()


@app.command("list")
def list_meetings(
    ctx: typer.Context,
    project: Optional[str] = typer.Option(None, "--project"),
    type: Optional[str] = typer.Option(None, "--type", "-t"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Toplantıları listele (en yeni önce)."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project) if project else None
        rows = meeting_model.list_meetings(conn, project_id, type)
        print_table("Toplantılar", rows, MEETING_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@app.command("add-action")
def add_action(
    ctx: typer.Context,
    meeting_id: int,
    description: str,
    owner: str = typer.Option(..., "--owner", "-o", help="Sorumlu kişi"),
    due: Optional[str] = typer.Option(None, "--due", help="YYYY-MM-DD"),
    task_id: Optional[int] = typer.Option(None, "--task"),
):
    """Bir toplantıya aksiyon maddesi ekle."""
    conn = get_conn(ctx)
    try:
        action = meeting_model.add_action_item(conn, meeting_id, description, owner, due, task_id)
        console.print(f"[green]Aksiyon eklendi:[/green] #{action.id} ({action.owner})")
    finally:
        conn.close()


@app.command("list-actions")
def list_actions(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    meeting_id: Optional[int] = typer.Option(None, "--meeting"),
    open_only: bool = typer.Option(False, "--open-only"),
    overdue_only: bool = typer.Option(False, "--overdue-only"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Aksiyon maddelerini listele."""
    import datetime

    conn = get_conn(ctx)
    try:
        status_filter = "open" if open_only and not status else status
        rows = meeting_model.list_action_items(
            conn,
            status=status_filter,
            meeting_id=meeting_id,
            overdue_only=overdue_only,
            today=datetime.date.today(),
        )
        print_table("Aksiyon Maddeleri", rows, ACTION_ITEM_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@app.command("close-action")
def close_action(ctx: typer.Context, action_id: int):
    """Bir aksiyon maddesini tamamlandı olarak işaretle."""
    conn = get_conn(ctx)
    try:
        meeting_model.close_action_item(conn, action_id)
        console.print(f"[green]Aksiyon #{action_id} kapatıldı.[/green]")
    finally:
        conn.close()
