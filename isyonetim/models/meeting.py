"""Meeting / ActionItem veri erişim katmanı."""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta

MEETING_TYPES = ("supplier", "customer", "accountant", "internal", "other")
ACTION_STATUSES = ("open", "done", "cancelled")


@dataclass
class Meeting:
    id: int
    project_id: int | None
    title: str
    meeting_type: str
    meeting_date: str
    participants: str | None
    agenda: str | None
    decisions: str | None
    created_at: str
    meeting_time: str | None = None
    reminder_sent_at: str | None = None


@dataclass
class ActionItem:
    id: int
    meeting_id: int
    task_id: int | None
    description: str
    owner: str
    due_date: str | None
    status: str
    created_at: str
    completed_at: str | None


def _meeting(row: sqlite3.Row) -> Meeting:
    return Meeting(**dict(row))


def _action_item(row: sqlite3.Row) -> ActionItem:
    return ActionItem(**dict(row))


def create_meeting(
    conn: sqlite3.Connection,
    title: str,
    meeting_date: str | date,
    meeting_type: str = "other",
    project_id: int | None = None,
    participants: str | None = None,
    agenda: str | None = None,
    decisions: str | None = None,
    meeting_time: str | None = None,
) -> Meeting:
    mdate = meeting_date.isoformat() if isinstance(meeting_date, date) else meeting_date
    with conn:
        cur = conn.execute(
            """INSERT INTO meetings (project_id, title, meeting_type, meeting_date,
                                      participants, agenda, decisions, meeting_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, title, meeting_type, mdate, participants, agenda, decisions, meeting_time),
        )
    return get_meeting(conn, cur.lastrowid)


def get_meeting(conn: sqlite3.Connection, meeting_id: int) -> Meeting | None:
    row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    return _meeting(row) if row else None


def list_meetings(
    conn: sqlite3.Connection,
    project_id: int | None = None,
    meeting_type: str | None = None,
    since: str | date | None = None,
) -> list[Meeting]:
    clauses = []
    params: list = []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if meeting_type:
        clauses.append("meeting_type = ?")
        params.append(meeting_type)
    if since is not None:
        s = since.isoformat() if isinstance(since, date) else since
        clauses.append("meeting_date >= ?")
        params.append(s)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM meetings {where} ORDER BY meeting_date DESC, id DESC", params
    ).fetchall()
    return [_meeting(r) for r in rows]


def list_meetings_needing_reminder(
    conn: sqlite3.Connection, today: str, now_hhmm: str, lead_minutes: int, grace_minutes: int = 5,
) -> list[Meeting]:
    """Bugün, saati belirtilmiş, henüz hatırlatması gönderilmemiş ve başlamasına
    `lead_minutes` dakikadan az kalmış (veya `grace_minutes` önce başlamış,
    kontrol aralığı yüzünden kaçırılmasın diye) toplantıları döner."""
    rows = conn.execute(
        """SELECT * FROM meetings
           WHERE meeting_date = ? AND meeting_time IS NOT NULL AND reminder_sent_at IS NULL
           ORDER BY meeting_time""",
        (today,),
    ).fetchall()
    meetings = [_meeting(r) for r in rows]

    def minutes_of(hhmm: str) -> int:
        h, m = hhmm.split(":")[:2]
        return int(h) * 60 + int(m)

    now_min = minutes_of(now_hhmm)
    due = []
    for m in meetings:
        try:
            meeting_min = minutes_of(m.meeting_time)
        except (ValueError, AttributeError):
            continue
        diff = meeting_min - now_min
        if -grace_minutes <= diff <= lead_minutes:
            due.append(m)
    return due


def mark_reminder_sent(conn: sqlite3.Connection, meeting_id: int) -> None:
    with conn:
        conn.execute(
            "UPDATE meetings SET reminder_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (meeting_id,),
        )


def get_next_upcoming_meeting(conn: sqlite3.Connection, within_days: int = 3) -> Meeting | None:
    """Şu andan itibaren (saati belirtilmiş, henüz geçmemiş) en yakın
    toplantıyı döner — dashboard'un "girişte bildir" özelliği için."""
    now = datetime.now()
    today_s = now.date().isoformat()
    end_s = (now.date() + timedelta(days=within_days)).isoformat()
    rows = conn.execute(
        """SELECT * FROM meetings
           WHERE meeting_date BETWEEN ? AND ? AND meeting_time IS NOT NULL
           ORDER BY meeting_date, meeting_time""",
        (today_s, end_s),
    ).fetchall()
    for row in rows:
        m = _meeting(row)
        try:
            meeting_dt = datetime.strptime(f"{m.meeting_date} {m.meeting_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if meeting_dt >= now:
            return m
    return None


def add_action_item(
    conn: sqlite3.Connection,
    meeting_id: int,
    description: str,
    owner: str,
    due_date: str | date | None = None,
    task_id: int | None = None,
) -> ActionItem:
    due = due_date.isoformat() if isinstance(due_date, date) else due_date
    with conn:
        cur = conn.execute(
            """INSERT INTO action_items (meeting_id, task_id, description, owner, due_date)
               VALUES (?, ?, ?, ?, ?)""",
            (meeting_id, task_id, description, owner, due),
        )
    return get_action_item(conn, cur.lastrowid)


def get_action_item(conn: sqlite3.Connection, action_item_id: int) -> ActionItem | None:
    row = conn.execute("SELECT * FROM action_items WHERE id = ?", (action_item_id,)).fetchone()
    return _action_item(row) if row else None


def list_action_items(
    conn: sqlite3.Connection,
    status: str | None = None,
    meeting_id: int | None = None,
    overdue_only: bool = False,
    today: str | date | None = None,
) -> list[ActionItem]:
    clauses = []
    params: list = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if meeting_id is not None:
        clauses.append("meeting_id = ?")
        params.append(meeting_id)
    if overdue_only:
        t = today.isoformat() if isinstance(today, date) else today
        clauses.append("status = 'open' AND due_date IS NOT NULL AND due_date < ?")
        params.append(t)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM action_items {where} ORDER BY due_date IS NULL, due_date, id", params
    ).fetchall()
    return [_action_item(r) for r in rows]


def set_action_item_status(conn: sqlite3.Connection, action_item_id: int, status: str) -> None:
    completed_at = "CURRENT_TIMESTAMP" if status == "done" else "NULL"
    with conn:
        conn.execute(
            f"UPDATE action_items SET status = ?, completed_at = {completed_at} WHERE id = ?",
            (status, action_item_id),
        )


def close_action_item(conn: sqlite3.Connection, action_item_id: int) -> None:
    set_action_item_status(conn, action_item_id, "done")
