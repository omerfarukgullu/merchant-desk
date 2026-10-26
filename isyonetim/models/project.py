"""Project / Phase / Task veri erişim katmanı.

Her fonksiyon dışarıdan bir sqlite3.Connection alır; bağlantıyı açıp
kapatmak çağıran tarafın (CLI komutu, test, dashboard) sorumluluğundadır.
Bu sayede modül tamamen bağımsız test edilebilir (in-memory db ile).
"""

import sqlite3
from dataclasses import dataclass
from datetime import date

STATUSES = ("planned", "in_progress", "completed", "on_hold")
PRIORITY_BUCKETS = ("today", "this_week", "backlog")


@dataclass
class Project:
    id: int
    name: str
    description: str | None
    goal: str | None
    status: str
    created_at: str
    updated_at: str


@dataclass
class Phase:
    id: int
    project_id: int
    name: str
    status: str
    order_index: int
    notes: str | None
    created_at: str
    updated_at: str


@dataclass
class Task:
    id: int
    project_id: int
    phase_id: int | None
    title: str
    description: str | None
    status: str
    priority_bucket: str
    due_date: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


def _project(row: sqlite3.Row) -> Project:
    return Project(**dict(row))


def _phase(row: sqlite3.Row) -> Phase:
    return Phase(**dict(row))


def _task(row: sqlite3.Row) -> Task:
    return Task(**dict(row))


def create_project(
    conn: sqlite3.Connection,
    name: str,
    description: str | None = None,
    goal: str | None = None,
    status: str = "planned",
) -> Project:
    with conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description, goal, status) VALUES (?, ?, ?, ?)",
            (name, description, goal, status),
        )
    return get_project(conn, cur.lastrowid)


def get_project(conn: sqlite3.Connection, project_id: int) -> Project | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project(row) if row else None


def get_project_by_name(conn: sqlite3.Connection, name: str) -> Project | None:
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    return _project(row) if row else None


def list_projects(conn: sqlite3.Connection, status: str | None = None) -> list[Project]:
    if status:
        rows = conn.execute(
            "SELECT * FROM projects WHERE status = ? ORDER BY name", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    return [_project(r) for r in rows]


def update_project_status(conn: sqlite3.Connection, project_id: int, status: str) -> None:
    with conn:
        conn.execute(
            "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, project_id),
        )


def create_phase(
    conn: sqlite3.Connection,
    project_id: int,
    name: str,
    status: str = "planned",
    order_index: int = 0,
    notes: str | None = None,
) -> Phase:
    with conn:
        cur = conn.execute(
            """INSERT INTO phases (project_id, name, status, order_index, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, name, status, order_index, notes),
        )
    return get_phase(conn, cur.lastrowid)


def get_phase(conn: sqlite3.Connection, phase_id: int) -> Phase | None:
    row = conn.execute("SELECT * FROM phases WHERE id = ?", (phase_id,)).fetchone()
    return _phase(row) if row else None


def list_phases(conn: sqlite3.Connection, project_id: int | None = None) -> list[Phase]:
    if project_id is not None:
        rows = conn.execute(
            "SELECT * FROM phases WHERE project_id = ? ORDER BY order_index, id",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM phases ORDER BY project_id, order_index, id").fetchall()
    return [_phase(r) for r in rows]


def update_phase_status(conn: sqlite3.Connection, phase_id: int, status: str) -> None:
    with conn:
        conn.execute(
            "UPDATE phases SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, phase_id),
        )


def create_task(
    conn: sqlite3.Connection,
    project_id: int,
    title: str,
    phase_id: int | None = None,
    description: str | None = None,
    priority_bucket: str = "backlog",
    due_date: str | date | None = None,
    status: str = "planned",
) -> Task:
    due = due_date.isoformat() if isinstance(due_date, date) else due_date
    with conn:
        cur = conn.execute(
            """INSERT INTO tasks (project_id, phase_id, title, description, status,
                                   priority_bucket, due_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, phase_id, title, description, status, priority_bucket, due),
        )
    return get_task(conn, cur.lastrowid)


def get_task(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _task(row) if row else None


def list_tasks(
    conn: sqlite3.Connection,
    project_id: int | None = None,
    status: str | None = None,
    priority_bucket: str | None = None,
    exclude_completed: bool = False,
    due_before: str | date | None = None,
) -> list[Task]:
    clauses = []
    params: list = []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority_bucket:
        clauses.append("priority_bucket = ?")
        params.append(priority_bucket)
    if exclude_completed:
        clauses.append("status != 'completed'")
    if due_before is not None:
        due = due_before.isoformat() if isinstance(due_before, date) else due_before
        clauses.append("due_date IS NOT NULL AND due_date <= ?")
        params.append(due)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM tasks {where} ORDER BY due_date IS NULL, due_date, id", params
    ).fetchall()
    return [_task(r) for r in rows]


def update_task_status(conn: sqlite3.Connection, task_id: int, status: str) -> None:
    completed_at = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
    with conn:
        conn.execute(
            f"""UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP,
                                  completed_at = {completed_at}
                WHERE id = ?""",
            (status, task_id),
        )


def update_task_priority(conn: sqlite3.Connection, task_id: int, priority_bucket: str) -> None:
    with conn:
        conn.execute(
            "UPDATE tasks SET priority_bucket = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (priority_bucket, task_id),
        )
