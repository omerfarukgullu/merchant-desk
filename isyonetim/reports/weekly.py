"""Haftalık özet: proje/görev, toplantı/aksiyon ve e-ticaret modüllerini birleştirir."""

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from isyonetim.models import ecommerce as eco_model
from isyonetim.models import meeting as meeting_model
from isyonetim.models import project as project_model


@dataclass
class ChannelTotal:
    channel_name: str
    quantity: int
    revenue: float


@dataclass
class ProductTotal:
    product_name: str
    quantity: int
    revenue: float
    profit: float | None


def _period(start: date | None, end: date | None) -> tuple[date, date]:
    end = end or date.today()
    start = start or (end - timedelta(days=6))
    return start, end


def build_weekly_summary(
    conn: sqlite3.Connection, start: date | None = None, end: date | None = None
) -> dict:
    start, end = _period(start, end)
    start_s, end_s = start.isoformat(), end.isoformat()
    today_s = date.today().isoformat()

    all_tasks = project_model.list_tasks(conn)
    completed_tasks = [
        t for t in all_tasks
        if t.status == "completed" and t.completed_at and start_s <= t.completed_at[:10] <= end_s
    ]
    overdue_tasks = [
        t for t in all_tasks
        if t.status != "completed" and t.due_date and t.due_date < today_s
    ]
    in_progress_tasks = [t for t in all_tasks if t.status == "in_progress"]

    open_actions = meeting_model.list_action_items(conn, status="open")
    overdue_actions = [a for a in open_actions if a.due_date and a.due_date < today_s]

    sales = eco_model.list_sales(conn, since=start_s, until=end_s)
    products = {p.id: p for p in eco_model.list_products(conn)}
    channels = {c.id: c for c in eco_model.list_channels(conn)}

    channel_totals: dict[int, ChannelTotal] = {}
    product_totals: dict[int, ProductTotal] = {}
    total_revenue = 0.0
    total_profit = 0.0
    profit_known = True

    for sale in sales:
        revenue = sale.unit_price * sale.quantity
        cost = sale.unit_cost
        if cost is None:
            product = products.get(sale.product_id)
            cost = product.cost_price if product else None
        profit = None if cost is None else round((sale.unit_price - cost) * sale.quantity, 2)
        if profit is None:
            profit_known = False

        channel = channels.get(sale.channel_id)
        channel_name = channel.name if channel else f"#{sale.channel_id}"
        ct = channel_totals.setdefault(sale.channel_id, ChannelTotal(channel_name, 0, 0.0))
        ct.quantity += sale.quantity
        ct.revenue += revenue

        product = products.get(sale.product_id)
        product_name = product.name if product else f"#{sale.product_id}"
        pt = product_totals.setdefault(
            sale.product_id, ProductTotal(product_name, 0, 0.0, 0.0 if profit is not None else None)
        )
        pt.quantity += sale.quantity
        pt.revenue += revenue
        if pt.profit is not None and profit is not None:
            pt.profit += profit
        elif profit is None:
            pt.profit = None

        total_revenue += revenue
        if profit is not None:
            total_profit += profit

    top_selling = sorted(product_totals.values(), key=lambda p: p.quantity, reverse=True)[:5]
    top_profit = sorted(
        [p for p in product_totals.values() if p.profit is not None],
        key=lambda p: p.profit,
        reverse=True,
    )[:5]

    return {
        "start": start_s,
        "end": end_s,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "in_progress_tasks": in_progress_tasks,
        "overdue_actions": overdue_actions,
        "sales_count": len(sales),
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2) if profit_known else None,
        "channel_totals": sorted(channel_totals.values(), key=lambda c: c.revenue, reverse=True),
        "top_selling_products": top_selling,
        "top_profit_products": top_profit,
    }
