"""Bugün / haftalık özetleri .xlsx (Excel) dosyası olarak bellekte üretir.

Sadece dashboard kullanır — CLI pandas'a bağımlı kalmasın diye ayrı bir
modülde (CLI'nin CSV dışa aktarımı zaten stdlib `csv` ile, reports/export.py
üzerinden çalışıyor).
"""

import dataclasses
import io

import pandas as pd


def _df(rows: list) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dataclasses.asdict(r) for r in rows])


def build_today_excel(summary: dict) -> bytes:
    """build_today_summary() çıktısını çok sayfalı bir .xlsx'e yazar."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _df(summary["tasks"]).to_excel(writer, sheet_name="Görevler", index=False)
        _df(summary["meetings_today"]).to_excel(writer, sheet_name="Toplantılar", index=False)
        actions = summary["due_today_actions"] + summary["overdue_actions"]
        _df(actions).to_excel(writer, sheet_name="Aksiyonlar", index=False)
    return buffer.getvalue()


def build_weekly_excel(summary: dict) -> bytes:
    """build_weekly_summary() çıktısını çok sayfalı bir .xlsx'e yazar."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _df(summary["completed_tasks"]).to_excel(writer, sheet_name="Tamamlanan Görevler", index=False)
        _df(summary["overdue_tasks"]).to_excel(writer, sheet_name="Geciken Görevler", index=False)
        _df(summary["in_progress_tasks"]).to_excel(writer, sheet_name="Devam Eden Görevler", index=False)
        _df(summary["overdue_actions"]).to_excel(writer, sheet_name="Geciken Aksiyonlar", index=False)
        _df(summary["channel_totals"]).to_excel(writer, sheet_name="Kanal Bazlı Satış", index=False)
        _df(summary["top_selling_products"]).to_excel(writer, sheet_name="En Çok Satan", index=False)
        _df(summary["top_profit_products"]).to_excel(writer, sheet_name="En Çok Kâr Eden", index=False)
    return buffer.getvalue()
