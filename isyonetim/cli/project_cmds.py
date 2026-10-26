"""`isyonetim project ...` komutları: Project / Phase / Task."""

from typing import Optional

import typer

from isyonetim.cli.common import (
    PHASE_COLUMNS,
    PROJECT_COLUMNS,
    TASK_COLUMNS,
    console,
    err_console,
    get_conn,
    maybe_export_csv,
    print_table,
)
from isyonetim.models import project as project_model

app = typer.Typer(help="Proje (gelir kolu), aşama ve görev yönetimi.")


def _resolve_project_id(conn, identifier: str) -> int:
    if identifier.isdigit():
        proj = project_model.get_project(conn, int(identifier))
        if proj:
            return proj.id
    proj = project_model.get_project_by_name(conn, identifier)
    if proj:
        return proj.id
    err_console.print(f"Proje bulunamadı: {identifier!r}")
    raise typer.Exit(code=1)


@app.command("add")
def add_project(
    ctx: typer.Context,
    name: str,
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    goal: Optional[str] = typer.Option(None, "--goal", "-g"),
    status: str = typer.Option("planned", "--status", "-s"),
):
    """Yeni proje / gelir kolu ekle."""
    conn = get_conn(ctx)
    try:
        proj = project_model.create_project(conn, name, description, goal, status)
        console.print(f"[green]Proje eklendi:[/green] #{proj.id} {proj.name}")
    finally:
        conn.close()


@app.command("list")
def list_projects(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Projeleri listele."""
    conn = get_conn(ctx)
    try:
        rows = project_model.list_projects(conn, status)
        print_table("Projeler", rows, PROJECT_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@app.command("set-status")
def set_project_status(ctx: typer.Context, project: str, status: str):
    """Proje durumunu güncelle (planned/in_progress/completed/on_hold)."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project)
        project_model.update_project_status(conn, project_id, status)
        console.print(f"[green]Proje #{project_id} durumu güncellendi:[/green] {status}")
    finally:
        conn.close()


@app.command("add-phase")
def add_phase(
    ctx: typer.Context,
    project: str,
    name: str,
    status: str = typer.Option("planned", "--status", "-s"),
    order: int = typer.Option(0, "--order", "-o"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    """Bir projeye aşama ekle."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project)
        phase = project_model.create_phase(conn, project_id, name, status, order, notes)
        console.print(f"[green]Aşama eklendi:[/green] #{phase.id} {phase.name}")
    finally:
        conn.close()


@app.command("list-phases")
def list_phases(
    ctx: typer.Context,
    project: Optional[str] = typer.Argument(None),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Aşamaları listele (proje verilmezse tüm projeler)."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project) if project else None
        rows = project_model.list_phases(conn, project_id)
        print_table("Aşamalar", rows, PHASE_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@app.command("set-phase-status")
def set_phase_status(ctx: typer.Context, phase_id: int, status: str):
    """Aşama durumunu güncelle."""
    conn = get_conn(ctx)
    try:
        project_model.update_phase_status(conn, phase_id, status)
        console.print(f"[green]Aşama #{phase_id} durumu güncellendi:[/green] {status}")
    finally:
        conn.close()


@app.command("add-task")
def add_task(
    ctx: typer.Context,
    project: str,
    title: str,
    phase_id: Optional[int] = typer.Option(None, "--phase"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    priority: str = typer.Option("backlog", "--priority", "-p", help="today/this_week/backlog"),
    due: Optional[str] = typer.Option(None, "--due", help="YYYY-MM-DD"),
):
    """Bir projeye görev ekle."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project)
        task = project_model.create_task(
            conn, project_id, title, phase_id, description, priority, due
        )
        console.print(f"[green]Görev eklendi:[/green] #{task.id} {task.title}")
    finally:
        conn.close()


@app.command("list-tasks")
def list_tasks(
    ctx: typer.Context,
    project: Optional[str] = typer.Option(None, "--project"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p"),
    open_only: bool = typer.Option(False, "--open-only", help="Tamamlanmışları gizle"),
    csv: Optional[str] = typer.Option(None, "--csv"),
):
    """Görevleri listele."""
    conn = get_conn(ctx)
    try:
        project_id = _resolve_project_id(conn, project) if project else None
        rows = project_model.list_tasks(
            conn,
            project_id=project_id,
            status=status,
            priority_bucket=priority,
            exclude_completed=open_only,
        )
        print_table("Görevler", rows, TASK_COLUMNS)
        maybe_export_csv(rows, csv)
    finally:
        conn.close()


@app.command("set-task-status")
def set_task_status(ctx: typer.Context, task_id: int, status: str):
    """Görev durumunu güncelle (planned/in_progress/completed/on_hold)."""
    conn = get_conn(ctx)
    try:
        project_model.update_task_status(conn, task_id, status)
        console.print(f"[green]Görev #{task_id} durumu güncellendi:[/green] {status}")
    finally:
        conn.close()


@app.command("set-task-priority")
def set_task_priority(ctx: typer.Context, task_id: int, priority: str):
    """Görev önceliğini güncelle (today/this_week/backlog)."""
    conn = get_conn(ctx)
    try:
        project_model.update_task_priority(conn, task_id, priority)
        console.print(f"[green]Görev #{task_id} önceliği güncellendi:[/green] {priority}")
    finally:
        conn.close()
