"""models/: proje-aşama-görev, toplantı-aksiyon ve e-ticaret veri katmanı."""

import sqlite3
from datetime import date, datetime, timedelta

import pytest

from isyonetim.models import ecommerce as eco
from isyonetim.models import meeting as mtg
from isyonetim.models import project as proj

# ---------------------------------------------------------------- proje / görev

def test_create_and_fetch_project(conn):
    created = proj.create_project(conn, "Kahve Satışı", goal="Aylık 100 sipariş")

    assert created.id > 0
    assert created.status == "planned"
    assert proj.get_project(conn, created.id).name == "Kahve Satışı"
    assert proj.get_project_by_name(conn, "Kahve Satışı").id == created.id
    assert proj.get_project_by_name(conn, "Olmayan") is None


def test_project_name_is_unique(conn):
    proj.create_project(conn, "Tek")
    with pytest.raises(sqlite3.IntegrityError):
        proj.create_project(conn, "Tek")


def test_invalid_status_rejected_by_check_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        proj.create_project(conn, "Proje", status="bilinmeyen_durum")


def test_completing_a_task_sets_and_clears_completed_at(conn):
    p = proj.create_project(conn, "P")
    task = proj.create_task(conn, p.id, "Görev")
    assert task.completed_at is None

    proj.update_task_status(conn, task.id, "completed")
    assert proj.get_task(conn, task.id).completed_at is not None

    # Geri alınca completed_at temizlenmeli, yoksa haftalık özet
    # tamamlanmamış görevi "tamamlandı" sayar
    proj.update_task_status(conn, task.id, "in_progress")
    assert proj.get_task(conn, task.id).completed_at is None


def test_task_filters(conn):
    p = proj.create_project(conn, "P")
    proj.create_task(conn, p.id, "Bugün", priority_bucket="today", due_date=date(2026, 1, 10))
    proj.create_task(conn, p.id, "Bu hafta", priority_bucket="this_week")
    done = proj.create_task(conn, p.id, "Bitti", priority_bucket="today")
    proj.update_task_status(conn, done.id, "completed")

    assert len(proj.list_tasks(conn, project_id=p.id)) == 3
    assert len(proj.list_tasks(conn, priority_bucket="today")) == 2
    assert len(proj.list_tasks(conn, priority_bucket="today", exclude_completed=True)) == 1
    assert {t.title for t in proj.list_tasks(conn, due_before="2026-01-10")} == {"Bugün"}
    assert proj.list_tasks(conn, status="completed")[0].title == "Bitti"


def test_tasks_without_due_date_sort_last(conn):
    p = proj.create_project(conn, "P")
    proj.create_task(conn, p.id, "Tarihsiz")
    proj.create_task(conn, p.id, "Tarihli", due_date="2026-03-01")

    assert [t.title for t in proj.list_tasks(conn)] == ["Tarihli", "Tarihsiz"]


def test_phases_are_ordered_and_cascade_delete(conn):
    p = proj.create_project(conn, "P")
    proj.create_phase(conn, p.id, "İkinci", order_index=2)
    proj.create_phase(conn, p.id, "Birinci", order_index=1)

    assert [ph.name for ph in proj.list_phases(conn, p.id)] == ["Birinci", "İkinci"]

    with conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (p.id,))
    assert proj.list_phases(conn, p.id) == []


def test_deleting_phase_keeps_task_but_nulls_phase_id(conn):
    p = proj.create_project(conn, "P")
    ph = proj.create_phase(conn, p.id, "Aşama")
    task = proj.create_task(conn, p.id, "Görev", phase_id=ph.id)

    with conn:
        conn.execute("DELETE FROM phases WHERE id = ?", (ph.id,))

    assert proj.get_task(conn, task.id).phase_id is None


# ----------------------------------------------------------- toplantı / aksiyon

def test_meeting_with_date_object_and_time(conn):
    m = mtg.create_meeting(conn, "Görüşme", date(2026, 5, 4), meeting_time="09:30")

    assert m.meeting_date == "2026-05-04"
    assert m.meeting_time == "09:30"
    assert m.reminder_sent_at is None


def test_meetings_listed_newest_first(conn):
    mtg.create_meeting(conn, "Eski", "2026-01-01")
    mtg.create_meeting(conn, "Yeni", "2026-02-01")

    assert [m.title for m in mtg.list_meetings(conn)] == ["Yeni", "Eski"]
    assert [m.title for m in mtg.list_meetings(conn, since="2026-01-15")] == ["Yeni"]


def test_action_item_close_sets_completed_at(conn):
    m = mtg.create_meeting(conn, "T", "2026-01-01")
    a = mtg.add_action_item(conn, m.id, "Teklif iste", owner="Yönetici")

    assert a.status == "open"
    mtg.close_action_item(conn, a.id)

    closed = mtg.get_action_item(conn, a.id)
    assert closed.status == "done"
    assert closed.completed_at is not None


def test_overdue_action_filter(conn):
    m = mtg.create_meeting(conn, "T", "2026-01-01")
    mtg.add_action_item(conn, m.id, "Geciken", owner="A", due_date="2026-01-05")
    mtg.add_action_item(conn, m.id, "Gelecek", owner="A", due_date="2026-12-31")
    mtg.add_action_item(conn, m.id, "Tarihsiz", owner="A")

    overdue = mtg.list_action_items(conn, overdue_only=True, today="2026-06-01")

    assert [a.description for a in overdue] == ["Geciken"]


def test_reminder_window_includes_upcoming_excludes_far_and_sent(conn):
    mtg.create_meeting(conn, "10 dk sonra", "2026-04-01", meeting_time="10:10")
    mtg.create_meeting(conn, "2 saat sonra", "2026-04-01", meeting_time="12:00")
    mtg.create_meeting(conn, "Saatsiz", "2026-04-01")
    already = mtg.create_meeting(conn, "Bildirilmiş", "2026-04-01", meeting_time="10:05")
    mtg.mark_reminder_sent(conn, already.id)

    due = mtg.list_meetings_needing_reminder(
        conn, "2026-04-01", "10:00", lead_minutes=15,
    )

    assert [m.title for m in due] == ["10 dk sonra"]


def test_reminder_grace_catches_just_started_meeting(conn):
    mtg.create_meeting(conn, "3 dk önce başladı", "2026-04-01", meeting_time="09:57")

    due = mtg.list_meetings_needing_reminder(
        conn, "2026-04-01", "10:00", lead_minutes=15, grace_minutes=5,
    )

    assert len(due) == 1


def test_mark_reminder_sent_prevents_duplicate(conn):
    m = mtg.create_meeting(conn, "T", "2026-04-01", meeting_time="10:10")
    mtg.mark_reminder_sent(conn, m.id)

    assert mtg.list_meetings_needing_reminder(conn, "2026-04-01", "10:00", 15) == []
    assert mtg.get_meeting(conn, m.id).reminder_sent_at is not None


def test_next_upcoming_meeting_skips_past_and_timeless(conn):
    soon = datetime.now() + timedelta(hours=2)
    mtg.create_meeting(conn, "Geçmiş", (date.today() - timedelta(days=1)).isoformat(), meeting_time="09:00")
    mtg.create_meeting(conn, "Saatsiz", date.today().isoformat())
    mtg.create_meeting(conn, "Yaklaşan", soon.date().isoformat(), meeting_time=soon.strftime("%H:%M"))

    nxt = mtg.get_next_upcoming_meeting(conn)

    assert nxt is not None
    assert nxt.title == "Yaklaşan"


def test_next_upcoming_meeting_none_when_empty(conn):
    assert mtg.get_next_upcoming_meeting(conn) is None


# ------------------------------------------------------------------ e-ticaret

def test_listing_upsert_updates_instead_of_duplicating(conn):
    p = eco.create_product(conn, "Ürün A")
    c = eco.create_channel(conn, "Pazar Yeri")

    eco.upsert_listing(conn, p.id, c.id, price=100)
    updated = eco.upsert_listing(conn, p.id, c.id, price=120, status="out_of_stock")

    listings = eco.list_listings(conn, product_id=p.id)
    assert len(listings) == 1
    assert updated.price == 120
    assert updated.status == "out_of_stock"


def test_sku_must_be_unique(conn):
    eco.create_product(conn, "A", sku="SKU-1")
    with pytest.raises(sqlite3.IntegrityError):
        eco.create_product(conn, "B", sku="SKU-1")


def test_own_price_requires_channel_and_no_competitor(conn):
    p = eco.create_product(conn, "Ürün")

    # 'own' kaydı kanalsız olamaz (şemadaki CHECK)
    with pytest.raises(sqlite3.IntegrityError):
        eco.add_price_record(conn, p.id, 100, source="own")


def test_competitor_price_requires_competitor_name(conn):
    p = eco.create_product(conn, "Ürün")

    with pytest.raises(sqlite3.IntegrityError):
        eco.add_price_record(conn, p.id, 100, source="competitor")


def test_latest_price_comparison_returns_only_newest_per_source(conn):
    p = eco.create_product(conn, "Ürün")
    c = eco.create_channel(conn, "Kanal")

    eco.add_price_record(conn, p.id, 500, channel_id=c.id, source="own", recorded_at="2026-01-01")
    eco.add_price_record(conn, p.id, 550, channel_id=c.id, source="own", recorded_at="2026-02-01")
    eco.add_price_record(conn, p.id, 490, source="competitor", competitor_name="Rakip 1", recorded_at="2026-01-01")
    eco.add_price_record(conn, p.id, 530, source="competitor", competitor_name="Rakip 1", recorded_at="2026-02-01")
    eco.add_price_record(conn, p.id, 600, source="competitor", competitor_name="Rakip 2")

    result = eco.latest_price_comparison(conn, p.id)

    assert [r["price"] for r in result["own"]] == [550]
    assert result["own"][0]["channel_name"] == "Kanal"
    assert {r["competitor_name"]: r["price"] for r in result["competitors"]} == {
        "Rakip 1": 530, "Rakip 2": 600,
    }


def test_sale_profit_uses_sale_cost_then_fallback(conn):
    p = eco.create_product(conn, "Ürün", cost_price=100)
    c = eco.create_channel(conn, "Kanal")

    with_cost = eco.add_sale(conn, p.id, c.id, "2026-01-01", 2, 150, unit_cost=120)
    without_cost = eco.add_sale(conn, p.id, c.id, "2026-01-02", 2, 150)

    assert eco.sale_profit(with_cost) == 60           # (150-120) * 2
    assert eco.sale_profit(without_cost) is None      # maliyet bilinmiyor
    assert eco.sale_profit(without_cost, fallback_cost=100) == 100  # (150-100) * 2


def test_sale_date_range_filter(conn):
    p = eco.create_product(conn, "Ürün")
    c = eco.create_channel(conn, "Kanal")
    eco.add_sale(conn, p.id, c.id, "2026-01-01", 1, 10)
    eco.add_sale(conn, p.id, c.id, "2026-02-01", 1, 10)
    eco.add_sale(conn, p.id, c.id, "2026-03-01", 1, 10)

    assert len(eco.list_sales(conn, since="2026-01-15", until="2026-02-15")) == 1
    assert len(eco.list_sales(conn, since="2026-01-15")) == 2


def test_channel_with_sales_cannot_be_deleted(conn):
    """sale_records.channel_id ON DELETE RESTRICT: kanal silinince satış
    geçmişi sessizce bozulmasın."""
    p = eco.create_product(conn, "Ürün")
    c = eco.create_channel(conn, "Kanal")
    eco.add_sale(conn, p.id, c.id, "2026-01-01", 1, 10)

    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("DELETE FROM channels WHERE id = ?", (c.id,))
