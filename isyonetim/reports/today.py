"""'Bugün ne var' özeti: üç modülü (proje/görev, toplantı/aksiyon) tek ekranda toplar."""

import sqlite3
from datetime import date, timedelta

from isyonetim.models import meeting as meeting_model
from isyonetim.models import project as project_model


def build_today_summary(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    today_str = today.isoformat()

    priority_tasks = project_model.list_tasks(conn, priority_bucket="today", exclude_completed=True)
    due_tasks = project_model.list_tasks(conn, due_before=today_str, exclude_completed=True)
    seen_ids = set()
    tasks = []
    for t in priority_tasks + due_tasks:
        if t.id not in seen_ids:
            seen_ids.add(t.id)
            tasks.append(t)

    meetings_today = [m for m in meeting_model.list_meetings(conn) if m.meeting_date == today_str]

    open_actions = meeting_model.list_action_items(conn, status="open")
    overdue_actions = [a for a in open_actions if a.due_date and a.due_date < today_str]
    due_today_actions = [a for a in open_actions if a.due_date == today_str]

    return {
        "date": today_str,
        "tasks": tasks,
        "meetings_today": meetings_today,
        "overdue_actions": overdue_actions,
        "due_today_actions": due_today_actions,
    }


def format_today_digest(summary: dict) -> str:
    """build_today_summary() çıktısını tek satırlık bir özet mesajına çevirir
    (tray_app.py'nin günlük bildirimi ve dashboard'un açılış bildirimi bunu
    paylaşır, iki yerde ayrı ayrı yazılmasın diye)."""
    task_count = len(summary["tasks"])
    meeting_count = len(summary["meetings_today"])
    overdue_count = len(summary["overdue_actions"])
    if task_count == meeting_count == overdue_count == 0:
        return "Bugün için planlanmış görev, toplantı veya geciken aksiyon yok."
    parts = []
    if task_count:
        parts.append(f"{task_count} görev")
    if meeting_count:
        parts.append(f"{meeting_count} toplantı")
    if overdue_count:
        parts.append(f"{overdue_count} geciken aksiyon")
    return "Bugün: " + ", ".join(parts)


def build_agenda_lists(conn: sqlite3.Connection, upcoming_days: int = 7, limit: int = 6) -> dict:
    """Sol panelde göstermek için: yaklaşan (bugün dahil, önümüzdeki
    `upcoming_days` gün) ve geçmiş/geciken (tamamlanmamış, son tarihi geçmiş)
    toplantı/görev/aksiyonları ayrı iki listede toplar. Her öğe
    {"etiket", "tarih", "sort_key"} içerir."""
    today = date.today()
    today_s = today.isoformat()
    end_s = (today + timedelta(days=upcoming_days)).isoformat()

    upcoming: list[dict] = []
    overdue: list[dict] = []

    for m in meeting_model.list_meetings(conn, since=today_s):
        if m.meeting_date > end_s:
            continue
        when = f"{m.meeting_date} {m.meeting_time}" if m.meeting_time else m.meeting_date
        sort_key = m.meeting_date + (m.meeting_time or "00:00")
        upcoming.append({"etiket": f"🤝 {m.title}", "tarih": when, "sort_key": sort_key})

    for t in project_model.list_tasks(conn, exclude_completed=True):
        if not t.due_date:
            continue
        if today_s <= t.due_date <= end_s:
            upcoming.append({"etiket": f"📋 {t.title}", "tarih": t.due_date, "sort_key": t.due_date + "12:00"})
        elif t.due_date < today_s:
            overdue.append({"etiket": f"📋 {t.title}", "tarih": t.due_date, "sort_key": t.due_date})

    for a in meeting_model.list_action_items(conn, status="open"):
        if not a.due_date:
            continue
        if today_s <= a.due_date <= end_s:
            upcoming.append({"etiket": f"☑️ {a.description}", "tarih": a.due_date, "sort_key": a.due_date + "12:00"})
        elif a.due_date < today_s:
            overdue.append({"etiket": f"☑️ {a.description}", "tarih": a.due_date, "sort_key": a.due_date})

    upcoming.sort(key=lambda x: x["sort_key"])
    overdue.sort(key=lambda x: x["sort_key"], reverse=True)  # en son geciken üstte

    return {"upcoming": upcoming[:limit], "overdue": overdue[:limit]}
