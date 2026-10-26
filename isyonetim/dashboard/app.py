"""Streamlit arayüzü — okuma + yazma (ekleme/düzenleme).

CLI'den (isyonetim.cli) tamamen bağımsızdır — sadece isyonetim.models ve
isyonetim.reports altındaki (Typer'a bağımlı olmayan) saf veri katmanını
kullanır. Veritabanı yoksa otomatik oluşturur/migration uygular, bu yüzden
sadece bu dashboard (ya da paketlenmiş masaüstü uygulaması) ile de
çalışılabilir; CLI'nin önceden çalıştırılmış olması gerekmez.

Gezinme: st.navigation ile sol panelde bir menü olarak sunulur (üstte sayfa
geçişleri, altta ⚙️ Ayarlar sabitlenmiş). Sayfalar tek dosyada fonksiyon
olarak tanımlı; ayrı dosyalara bölünmesi gerekmiyor.

Çalıştırma (geliştirme):
    streamlit run isyonetim/dashboard/app.py
"""

import calendar as calendar_module
import html
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from isyonetim import config
from isyonetim import settings as settings_module
from isyonetim.core import db
from isyonetim.dashboard.theme_css import CUSTOM_CSS
from isyonetim.models import ecommerce as eco_model
from isyonetim.models import meeting as meeting_model
from isyonetim.models import project as project_model
from isyonetim.reports import excel_export
from isyonetim.reports.today import build_agenda_lists, build_today_summary, format_today_digest
from isyonetim.reports.weekly import build_weekly_summary

SETTINGS = settings_module.load_settings()

st.set_page_config(page_title=SETTINGS.panel_title, layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

STATUS_LABELS_TR = {
    "planned": "Planlandı", "in_progress": "Devam ediyor",
    "completed": "Tamamlandı", "on_hold": "Beklemede",
}
PRIORITY_LABELS_TR = {"today": "Bugün", "this_week": "Bu hafta", "backlog": "Birikmiş"}
MEETING_TYPE_LABELS_TR = {
    "supplier": "Tedarikçi", "customer": "Müşteri", "accountant": "Mali müşavir",
    "internal": "İç", "other": "Diğer",
}
ACTION_STATUS_LABELS_TR = {"open": "Açık", "done": "Kapandı", "cancelled": "İptal"}

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
TR_WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def relabel(series: pd.Series, mapping: dict) -> pd.Series:
    return series.rename(index=lambda k: mapping.get(k, k))


def rows_to_df(rows: list) -> pd.DataFrame:
    import dataclasses

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dataclasses.asdict(r) for r in rows])


def editable_status_table(df: pd.DataFrame, status_col: str, options: tuple, key: str) -> pd.DataFrame | None:
    """Sadece `status_col` düzenlenebilir olan bir tablo gösterir; None -> tablo boş."""
    if df.empty:
        st.caption("Kayıt yok.")
        return None
    edited = st.data_editor(
        df,
        column_config={status_col: st.column_config.SelectboxColumn(status_col, options=list(options))},
        disabled=[c for c in df.columns if c != status_col],
        hide_index=True,
        width="stretch",
        key=key,
    )
    return edited


def apply_status_changes(original: pd.DataFrame, edited: pd.DataFrame, id_col: str, status_col: str, update_fn) -> int:
    """original/edited satır sırası farklı olabilir (ör. sütun sıralaması); id ile eşleştir."""
    orig_by_id = dict(zip(original[id_col], original[status_col], strict=True))
    changed = 0
    for _, row in edited.iterrows():
        row_id = int(row[id_col])
        new_status = row[status_col]
        if orig_by_id.get(row_id) != new_status:
            update_fn(row_id, new_status)
            changed += 1
    return changed


INBOX_PROJECT_NAME = "📥 Gelen Kutusu"


def get_or_create_inbox_project(conn) -> int:
    """Sol paneldeki 'Hızlı ekle' kutusunun düştüğü, otomatik oluşturulan
    proje. Görevi hemen bir projeye/aşamaya atamak istemeyen kullanıcı için —
    sonradan Proje & Görev sayfasından düzenlenip taşınabilir."""
    existing = project_model.get_project_by_name(conn, INBOX_PROJECT_NAME)
    if existing:
        return existing.id
    created = project_model.create_project(
        conn, INBOX_PROJECT_NAME,
        description="Hızlı ekle ile eklenen, henüz kategorize edilmemiş görevler.",
        status="in_progress",
    )
    return created.id


conn: object = None  # st.navigation sayfa fonksiyonları çalışmadan önce aşağıda atanır.


# ============================================================================
# Sayfalar
# ============================================================================

def page_overview():
    today_summary = build_today_summary(conn)
    weekly = build_weekly_summary(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bugün yapılacak görev", len(today_summary["tasks"]))
    col2.metric("Süresi geçmiş aksiyon", len(today_summary["overdue_actions"]))
    col3.metric(SETTINGS.money_label("Bu hafta ciro"), f"{weekly['total_revenue']:,.0f}")
    profit_display = "—" if weekly["total_profit"] is None else f"{weekly['total_profit']:,.0f}"
    col4.metric(SETTINGS.money_label("Bu hafta kâr"), profit_display)

    st.subheader(f"Bugün — {today_summary['date']}")
    left, right = st.columns(2)
    with left:
        st.markdown("**Yapılacak görevler**")
        tdf = rows_to_df(today_summary["tasks"])
        st.dataframe(
            tdf[["id", "project_id", "title", "status", "priority_bucket", "due_date"]] if not tdf.empty else tdf,
            hide_index=True, width="stretch",
        )
    with right:
        st.markdown("**Süresi geçmiş / bugün vadeli aksiyonlar**")
        overdue_df = rows_to_df(today_summary["overdue_actions"])
        due_today_df = rows_to_df(today_summary["due_today_actions"])
        actions_df = (
            pd.concat([overdue_df, due_today_df], ignore_index=True)
            if not overdue_df.empty or not due_today_df.empty else pd.DataFrame()
        )
        st.dataframe(
            actions_df[["id", "description", "owner", "due_date", "status"]] if not actions_df.empty else actions_df,
            hide_index=True, width="stretch",
        )

    if today_summary["meetings_today"]:
        st.markdown("**Bugünkü toplantılar**")
        st.dataframe(rows_to_df(today_summary["meetings_today"]), hide_index=True, width="stretch")

    st.divider()
    trend_col, progress_col = st.columns(2)
    with trend_col:
        st.markdown("**Son 14 gün ciro trendi**")
        since_14 = (date.today() - timedelta(days=13)).isoformat()
        sales_14 = eco_model.list_sales(conn, since=since_14)
        if sales_14:
            sdf14 = rows_to_df(sales_14)
            sdf14["revenue"] = sdf14["unit_price"] * sdf14["quantity"]
            daily = sdf14.groupby("sale_date")["revenue"].sum()
            full_range = pd.date_range(end=date.today(), periods=14, freq="D").strftime("%Y-%m-%d")
            daily = daily.reindex(full_range, fill_value=0)
            daily.index.name = "tarih"
            st.line_chart(daily)
        else:
            st.caption("Son 14 günde satış kaydı yok.")
    with progress_col:
        st.markdown("**Proje ilerlemesi (tamamlanan görev %)**")
        progress_rows = []
        for proj in project_model.list_projects(conn):
            proj_tasks = project_model.list_tasks(conn, project_id=proj.id)
            if not proj_tasks:
                continue
            done = sum(1 for t in proj_tasks if t.status == "completed")
            progress_rows.append({"proje": proj.name, "tamamlanma_%": round(100 * done / len(proj_tasks), 1)})
        if progress_rows:
            progress_df = pd.DataFrame(progress_rows).set_index("proje")
            st.bar_chart(progress_df)
        else:
            st.caption("Görev içeren proje yok.")

    st.divider()
    st.markdown("**Dışa aktar**")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            "📥 Bugünü Excel olarak indir",
            data=excel_export.build_today_excel(today_summary),
            file_name=f"bugun_{today_summary['date']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with dl_col2:
        st.download_button(
            "📥 Bu haftayı Excel olarak indir",
            data=excel_export.build_weekly_excel(weekly),
            file_name=f"hafta_{weekly['start']}_{weekly['end']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def _calendar_entries_for_month(year: int, month: int) -> dict[str, list[dict]]:
    """Verilen ay için görev/toplantı/aksiyon kayıtlarını tarihe göre gruplar."""
    month_prefix = f"{year:04d}-{month:02d}"
    entries: dict[str, list[dict]] = {}

    def add(day: str, kind: str, label: str, sublabel: str = ""):
        entries.setdefault(day, []).append({"kind": kind, "label": label, "sublabel": sublabel})

    for t in project_model.list_tasks(conn):
        if t.due_date and t.due_date.startswith(month_prefix):
            add(t.due_date, "task", t.title, STATUS_LABELS_TR.get(t.status, t.status))

    for m in meeting_model.list_meetings(conn):
        if m.meeting_date and m.meeting_date.startswith(month_prefix):
            label = f"{m.meeting_time} {m.title}" if m.meeting_time else m.title
            add(m.meeting_date, "meeting", label, MEETING_TYPE_LABELS_TR.get(m.meeting_type, m.meeting_type))

    for a in meeting_model.list_action_items(conn):
        if a.due_date and a.due_date.startswith(month_prefix):
            add(a.due_date, "action", a.description, f"Sorumlu: {a.owner}" if a.owner else "")

    return entries


KIND_LABELS_TR = {"task": "Görev", "meeting": "Toplantı", "action": "Aksiyon"}
KIND_ICONS = {"task": "📋", "meeting": "🤝", "action": "☑️"}


def page_calendar():
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = date.today().year
        st.session_state.cal_month = date.today().month

    nav_prev, nav_label, nav_today, nav_next = st.columns([1, 4, 1, 1])
    with nav_prev:
        if st.button("◀", key="cal_prev"):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
    with nav_next:
        if st.button("▶", key="cal_next"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
    with nav_today:
        if st.button("Bugün", key="cal_today"):
            st.session_state.cal_year = date.today().year
            st.session_state.cal_month = date.today().month
    with nav_label:
        st.markdown(
            f"<h3 style='text-align:center;margin:0;'>"
            f"{TR_MONTHS[st.session_state.cal_month - 1]} {st.session_state.cal_year}</h3>",
            unsafe_allow_html=True,
        )

    year, month = st.session_state.cal_year, st.session_state.cal_month
    entries = _calendar_entries_for_month(year, month)
    today_str = date.today().isoformat()
    weeks = calendar_module.Calendar(firstweekday=0).monthdayscalendar(year, month)

    cells_html = "".join(f'<div class="iy-cal-weekday">{d}</div>' for d in TR_WEEKDAYS)
    for week in weeks:
        for day_num in week:
            if day_num == 0:
                cells_html += '<div class="iy-cal-day outside"></div>'
                continue
            day_str = f"{year:04d}-{month:02d}-{day_num:02d}"
            classes = "iy-cal-day"
            if day_str == today_str:
                classes += " today"
            notes_html = ""
            for e in entries.get(day_str, [])[:4]:
                notes_html += (
                    f'<div class="iy-cal-note iy-cal-note-{e["kind"]}" title="{html.escape(e["label"])}">'
                    f'{KIND_ICONS[e["kind"]]} {html.escape(e["label"])}</div>'
                )
            extra = len(entries.get(day_str, [])) - 4
            if extra > 0:
                notes_html += f'<div class="iy-cal-more">+{extra} daha</div>'
            cells_html += (
                f'<div class="{classes}"><div class="iy-cal-daynum">{day_num}</div>{notes_html}</div>'
            )

    st.markdown(f'<div class="iy-cal">{cells_html}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("**Bu ayın notları (tablo)**")
    rows = []
    for day_str in sorted(entries.keys()):
        for e in entries[day_str]:
            rows.append({
                "Tarih": day_str,
                "Tür": KIND_LABELS_TR[e["kind"]],
                "Not": e["label"],
                "Detay": e["sublabel"],
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.caption("Bu ayda tarihli kayıt yok.")


def page_projects():
    projects = project_model.list_projects(conn)
    all_tasks = project_model.list_tasks(conn)

    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    pcol1.metric("Toplam proje", len(projects))
    pcol2.metric("Devam eden görev", sum(1 for t in all_tasks if t.status == "in_progress"))
    pcol3.metric("Tamamlanan görev", sum(1 for t in all_tasks if t.status == "completed"))
    pcol4.metric(
        "Backlog",
        sum(1 for t in all_tasks if t.priority_bucket == "backlog" and t.status != "completed"),
    )

    if all_tasks:
        chart_col, status_col = st.columns(2)
        with chart_col:
            st.markdown("**Öncelik dağılımı (tüm projeler)**")
            priority_counts = pd.Series([t.priority_bucket for t in all_tasks]).value_counts()
            priority_counts = priority_counts.reindex(project_model.PRIORITY_BUCKETS, fill_value=0)
            priority_counts = relabel(priority_counts, PRIORITY_LABELS_TR)
            priority_counts.index.name = "öncelik"
            st.bar_chart(priority_counts.rename("görev sayısı"))
        with status_col:
            st.markdown("**Durum dağılımı (tüm görevler)**")
            status_counts = pd.Series([t.status for t in all_tasks]).value_counts()
            status_counts = status_counts.reindex(project_model.STATUSES, fill_value=0)
            status_counts = relabel(status_counts, STATUS_LABELS_TR)
            status_counts.index.name = "durum"
            st.bar_chart(status_counts.rename("görev sayısı"))

    st.divider()

    with st.expander("+ Yeni proje ekle"):
        with st.form("new_project_form", clear_on_submit=True):
            p_name = st.text_input("Proje adı")
            p_goal = st.text_input("Hedef")
            p_desc = st.text_area("Açıklama", height=80)
            p_status = st.selectbox("Durum", project_model.STATUSES)
            if st.form_submit_button("Ekle", type="primary") and p_name:
                project_model.create_project(conn, p_name, p_desc or None, p_goal or None, p_status)
                st.success(f"Proje eklendi: {p_name}")
                st.rerun()

    if not projects:
        st.info("Henüz proje eklenmemiş.")

    for p in projects:
        p_tasks_all = [t for t in all_tasks if t.project_id == p.id]
        p_done = sum(1 for t in p_tasks_all if t.status == "completed")
        progress_suffix = f" · {p_done}/{len(p_tasks_all)} görev tamamlandı" if p_tasks_all else ""
        with st.expander(f"{p.name} — {p.status}{progress_suffix}", expanded=False):
            if p.goal:
                st.markdown(f"*Hedef: {p.goal}*")

            new_status = st.selectbox(
                "Proje durumu", project_model.STATUSES,
                index=project_model.STATUSES.index(p.status), key=f"proj_status_{p.id}",
            )
            if new_status != p.status and st.button("Proje durumunu kaydet", key=f"proj_status_btn_{p.id}"):
                project_model.update_project_status(conn, p.id, new_status)
                st.rerun()

            phases = project_model.list_phases(conn, p.id)
            tasks = project_model.list_tasks(conn, project_id=p.id)

            pcol, tcol = st.columns(2)
            with pcol:
                st.markdown("**Aşamalar**")
                pdf = rows_to_df(phases)[["id", "name", "status", "order_index"]] if phases else pd.DataFrame()
                edited = editable_status_table(pdf, "status", project_model.STATUSES, key=f"phase_editor_{p.id}")
                if edited is not None and st.button("Aşama durumlarını kaydet", key=f"phase_save_{p.id}"):
                    n = apply_status_changes(pdf, edited, "id", "status", lambda i, s: project_model.update_phase_status(conn, i, s))
                    if n:
                        st.success(f"{n} aşama güncellendi.")
                        st.rerun()

                with st.form(f"new_phase_form_{p.id}", clear_on_submit=True):
                    ph_name = st.text_input("Yeni aşama adı", key=f"ph_name_{p.id}")
                    ph_order = st.number_input("Sıra", min_value=0, value=len(phases), step=1, key=f"ph_order_{p.id}")
                    if st.form_submit_button("Aşama ekle", type="primary") and ph_name:
                        project_model.create_phase(conn, p.id, ph_name, order_index=int(ph_order))
                        st.rerun()

            with tcol:
                st.markdown("**Görevler**")
                tdf = rows_to_df(tasks)[["id", "title", "status", "priority_bucket", "due_date"]] if tasks else pd.DataFrame()
                edited_t = editable_status_table(tdf, "status", project_model.STATUSES, key=f"task_editor_{p.id}")
                if edited_t is not None and st.button("Görev durumlarını kaydet", key=f"task_save_{p.id}"):
                    n = apply_status_changes(tdf, edited_t, "id", "status", lambda i, s: project_model.update_task_status(conn, i, s))
                    if n:
                        st.success(f"{n} görev güncellendi.")
                        st.rerun()

                with st.form(f"new_task_form_{p.id}", clear_on_submit=True):
                    t_title = st.text_input("Yeni görev", key=f"t_title_{p.id}")
                    phase_options = {"(aşamasız)": None} | {ph.name: ph.id for ph in phases}
                    t_phase = st.selectbox("Aşama", list(phase_options.keys()), key=f"t_phase_{p.id}")
                    t_priority = st.selectbox("Öncelik", project_model.PRIORITY_BUCKETS, key=f"t_priority_{p.id}")
                    t_due = st.date_input("Son tarih", value=None, key=f"t_due_{p.id}")
                    if st.form_submit_button("Görev ekle", type="primary") and t_title:
                        project_model.create_task(
                            conn, p.id, t_title, phase_id=phase_options[t_phase],
                            priority_bucket=t_priority, due_date=t_due,
                        )
                        st.rerun()


def page_meetings():
    meetings = meeting_model.list_meetings(conn)
    all_actions = meeting_model.list_action_items(conn)
    open_actions = [a for a in all_actions if a.status == "open"]
    today_str = date.today().isoformat()
    overdue_actions_all = [a for a in open_actions if a.due_date and a.due_date < today_str]

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Toplam toplantı", len(meetings))
    mcol2.metric("Açık aksiyon", len(open_actions))
    mcol3.metric("Süresi geçmiş aksiyon", len(overdue_actions_all))
    mcol4.metric("Kapatılan aksiyon", sum(1 for a in all_actions if a.status == "done"))

    if meetings or all_actions:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("**Toplantı türü dağılımı**")
            if meetings:
                type_counts = pd.Series([m.meeting_type for m in meetings]).value_counts()
                type_counts = relabel(type_counts, MEETING_TYPE_LABELS_TR)
                type_counts.index.name = "tür"
                st.bar_chart(type_counts.rename("adet"))
            else:
                st.caption("Henüz toplantı yok.")
        with chart_col2:
            st.markdown("**Aksiyon durumu dağılımı**")
            if all_actions:
                action_status_counts = pd.Series([a.status for a in all_actions]).value_counts()
                action_status_counts = action_status_counts.reindex(meeting_model.ACTION_STATUSES, fill_value=0)
                action_status_counts = relabel(action_status_counts, ACTION_STATUS_LABELS_TR)
                action_status_counts.index.name = "durum"
                st.bar_chart(action_status_counts.rename("adet"))
            else:
                st.caption("Henüz aksiyon yok.")

    st.divider()

    with st.expander("+ Yeni toplantı ekle"):
        with st.form("new_meeting_form", clear_on_submit=True):
            m_title = st.text_input("Başlık")
            m_type = st.selectbox("Tür", meeting_model.MEETING_TYPES)
            date_col, time_col = st.columns(2)
            m_date = date_col.date_input("Tarih", value=date.today())
            m_time = time_col.time_input("Saat (opsiyonel — hatırlatma için gerekli)", value=None)
            proj_options = {"(bağımsız)": None} | {p.name: p.id for p in project_model.list_projects(conn)}
            m_project = st.selectbox("Proje", list(proj_options.keys()))
            m_participants = st.text_input("Katılımcılar")
            m_agenda = st.text_area("Gündem", height=70)
            m_decisions = st.text_area("Alınan kararlar", height=70)
            if st.form_submit_button("Toplantı ekle", type="primary") and m_title:
                meeting_model.create_meeting(
                    conn, m_title, m_date, m_type, proj_options[m_project],
                    m_participants or None, m_agenda or None, m_decisions or None,
                    m_time.strftime("%H:%M") if m_time else None,
                )
                st.success("Toplantı eklendi.")
                st.rerun()

    st.markdown("**Toplantılar (en yeni önce)**")
    mdf = rows_to_df(meetings)
    st.dataframe(
        mdf[["id", "title", "meeting_type", "meeting_date", "meeting_time", "project_id"]] if not mdf.empty else mdf,
        hide_index=True, width="stretch",
    )

    if meetings:
        with st.expander("+ Aksiyon maddesi ekle"):
            with st.form("new_action_form", clear_on_submit=True):
                meeting_options = {f"#{m.id} — {m.title} ({m.meeting_date})": m.id for m in meetings}
                a_meeting = st.selectbox("Toplantı", list(meeting_options.keys()))
                a_desc = st.text_input("Aksiyon açıklaması")
                a_owner = st.text_input("Sorumlu", value=SETTINGS.owner_name)
                a_due = st.date_input("Son tarih", value=None, key="action_due")
                if st.form_submit_button("Aksiyon ekle", type="primary") and a_desc and a_owner:
                    meeting_model.add_action_item(conn, meeting_options[a_meeting], a_desc, a_owner, a_due)
                    st.success("Aksiyon eklendi.")
                    st.rerun()

    st.markdown("**Aksiyon maddeleri**")
    adf = rows_to_df(all_actions)[["id", "meeting_id", "description", "owner", "due_date", "status"]] if all_actions else pd.DataFrame()
    edited_a = editable_status_table(adf, "status", meeting_model.ACTION_STATUSES, key="action_editor")
    if edited_a is not None and st.button("Aksiyon durumlarını kaydet"):
        n = apply_status_changes(adf, edited_a, "id", "status", lambda i, s: meeting_model.set_action_item_status(conn, i, s))
        if n:
            st.success(f"{n} aksiyon güncellendi.")
            st.rerun()


def page_ecommerce():
    weekly = build_weekly_summary(conn)

    st.subheader("Kanal bazlı satış (bu hafta)")
    channel_df = rows_to_df(weekly["channel_totals"])
    if not channel_df.empty:
        st.bar_chart(channel_df.set_index("channel_name")["revenue"])
    else:
        st.info("Bu dönemde satış kaydı yok.")

    st.subheader("Ürün bazlı ciro / kâr (bu hafta, ilk 5)")
    product_df = rows_to_df(weekly["top_selling_products"])
    if not product_df.empty:
        chart_df = product_df.set_index("product_name")[["revenue", "profit"]].fillna(0)
        st.bar_chart(chart_df)
    else:
        st.info("Bu dönemde satış kaydı yok.")

    add_p, add_c = st.columns(2)
    with add_p:
        with st.expander("+ Yeni ürün ekle"):
            with st.form("new_product_form", clear_on_submit=True):
                pr_name = st.text_input("Ürün adı")
                pr_sku = st.text_input("SKU")
                pr_category = st.text_input("Kategori")
                pr_cost = st.number_input(SETTINGS.money_label("Maliyet"), min_value=0.0, step=1.0)
                if st.form_submit_button("Ürün ekle", type="primary") and pr_name:
                    eco_model.create_product(conn, pr_name, pr_sku or None, pr_category or None, pr_cost or None)
                    st.success("Ürün eklendi.")
                    st.rerun()
    with add_c:
        with st.expander("+ Yeni kanal ekle"):
            with st.form("new_channel_form", clear_on_submit=True):
                ch_name = st.text_input("Kanal adı")
                ch_type = st.selectbox("Tür", eco_model.CHANNEL_TYPES)
                if st.form_submit_button("Kanal ekle", type="primary") and ch_name:
                    eco_model.create_channel(conn, ch_name, ch_type)
                    st.success("Kanal eklendi.")
                    st.rerun()

    products = eco_model.list_products(conn)
    channels = eco_model.list_channels(conn)

    st.subheader("Ürünler")
    st.dataframe(rows_to_df(products), hide_index=True, width="stretch")

    st.subheader("Kanallar")
    st.dataframe(rows_to_df(channels), hide_index=True, width="stretch")

    if products and channels:
        product_options = {p.name: p.id for p in products}
        channel_options = {c.name: c.id for c in channels}

        st.subheader("Listeleme fiyatı/durumu güncelle")
        with st.form("listing_form", clear_on_submit=True):
            l_product = st.selectbox("Ürün", list(product_options.keys()), key="listing_product")
            l_channel = st.selectbox("Kanal", list(channel_options.keys()), key="listing_channel")
            l_price = st.number_input(SETTINGS.money_label("Fiyat"), min_value=0.0, step=1.0, key="listing_price")
            l_status = st.selectbox("Durum", eco_model.LISTING_STATUSES, key="listing_status")
            if st.form_submit_button("Listelemeyi kaydet", type="primary"):
                eco_model.upsert_listing(conn, product_options[l_product], channel_options[l_channel], l_price, l_status)
                st.success("Listeleme güncellendi.")
                st.rerun()

        st.subheader("Fiyat kaydı ekle (kendi fiyatım / rakip)")
        with st.form("price_form", clear_on_submit=True):
            pf_product = st.selectbox("Ürün", list(product_options.keys()), key="price_product")
            pf_source = st.radio("Kaynak", ["Kendi fiyatım", "Rakip fiyatı"], horizontal=True)
            pf_channel = None
            pf_competitor = None
            if pf_source == "Kendi fiyatım":
                pf_channel = st.selectbox("Kanal", list(channel_options.keys()), key="price_channel")
            else:
                pf_competitor = st.text_input("Rakip adı", placeholder="Rakip firma / mağaza adı")
            pf_price = st.number_input(SETTINGS.money_label("Fiyat"), min_value=0.0, step=1.0, key="price_value")
            if st.form_submit_button("Fiyat kaydet", type="primary"):
                if pf_source == "Kendi fiyatım":
                    eco_model.add_price_record(
                        conn, product_options[pf_product], pf_price,
                        channel_id=channel_options[pf_channel], source="own",
                    )
                elif pf_competitor:
                    eco_model.add_price_record(
                        conn, product_options[pf_product], pf_price,
                        source="competitor", competitor_name=pf_competitor,
                    )
                st.success("Fiyat kaydı eklendi.")
                st.rerun()

        st.subheader("Fiyat karşılaştırması")
        cmp_product = st.selectbox("Ürün seç", list(product_options.keys()), key="compare_product")
        comparison = eco_model.latest_price_comparison(conn, product_options[cmp_product])

        bars = [
            {"etiket": f"Ben — {row['channel_name']}", "fiyat": row["price"]}
            for row in comparison["own"]
        ] + [
            {"etiket": f"Rakip — {row['competitor_name']}", "fiyat": row["price"]}
            for row in comparison["competitors"]
        ]
        if bars:
            st.bar_chart(pd.DataFrame(bars).set_index("etiket"))
        else:
            st.caption("Bu ürün için henüz fiyat kaydı yok.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Kendi fiyatlarım**")
            st.dataframe(pd.DataFrame(comparison["own"]), hide_index=True, width="stretch")
        with c2:
            st.markdown("**Rakip fiyatları**")
            st.dataframe(pd.DataFrame(comparison["competitors"]), hide_index=True, width="stretch")

        st.subheader("Satış ekle")
        with st.form("sale_form", clear_on_submit=True):
            s_product = st.selectbox("Ürün", list(product_options.keys()), key="sale_product")
            s_channel = st.selectbox("Kanal", list(channel_options.keys()), key="sale_channel")
            s_qty = st.number_input("Adet", min_value=1, value=1, step=1)
            s_price = st.number_input(SETTINGS.money_label("Birim fiyat"), min_value=0.0, step=1.0, key="sale_price")
            s_date = st.date_input("Satış tarihi", value=date.today(), key="sale_date")
            s_cost = st.number_input(SETTINGS.money_label("Birim maliyet (opsiyonel)"), min_value=0.0, step=1.0, key="sale_cost")
            if st.form_submit_button("Satış ekle", type="primary"):
                eco_model.add_sale(
                    conn, product_options[s_product], channel_options[s_channel],
                    s_date, int(s_qty), s_price, s_cost or None,
                )
                st.success("Satış eklendi.")
                st.rerun()
    else:
        st.info("Fiyat/satış girmek için önce en az bir ürün ve bir kanal ekleyin.")

    st.subheader("Son satışlar")
    sales = eco_model.list_sales(conn)
    sdf = rows_to_df(sales)
    st.dataframe(
        sdf[["id", "product_id", "channel_id", "sale_date", "quantity", "unit_price"]] if not sdf.empty else sdf,
        hide_index=True, width="stretch",
    )


def page_settings():
    """İşletme ayarları — sistemin hangi işletmeye ait olduğunu burada belirlersiniz."""
    st.caption(
        "Bu ayarlar `data/settings.json` dosyasına yazılır; depoya girmez. "
        "Panel başlığı ve tüm tutar etiketleri buradan beslenir."
    )

    current = settings_module.load_settings()
    locked = settings_module.env_overrides()

    def lock_note(field: str) -> str:
        return (
            f" — ⚠️ `ISYONETIM_{field.upper()}` ortam değişkeniyle sabitlenmiş, "
            "kaydedilen değer bu çalıştırmada etkisiz kalır"
            if field in locked else ""
        )

    with st.form("settings_form"):
        st.markdown("**İşletme**")
        business_name = st.text_input(
            "İşletme adı" + lock_note("business_name"),
            value=current.business_name,
            help="Panel başlığında ve masaüstü pencere adında görünür.",
        )
        col_cur, col_owner = st.columns(2)
        currency = col_cur.text_input(
            "Para birimi" + lock_note("currency"),
            value=current.currency,
            help="Tutar etiketlerinde kullanılır (TL, EUR, USD, £ ...).",
        )
        owner_name = col_owner.text_input(
            "Varsayılan sorumlu" + lock_note("owner_name"),
            value=current.owner_name,
            help="Yeni aksiyon maddelerinde 'Sorumlu' alanına hazır gelir.",
        )

        st.markdown("**Hatırlatmalar** (arka plan hatırlatıcısı için)")
        col_lead, col_hour = st.columns(2)
        reminder_lead_minutes = col_lead.number_input(
            "Toplantıdan kaç dakika önce bildirim" + lock_note("reminder_lead_minutes"),
            min_value=1, max_value=240, step=5, value=current.reminder_lead_minutes,
        )
        digest_after_hour = col_hour.number_input(
            "Günlük özet saati" + lock_note("digest_after_hour"),
            min_value=0, max_value=23, step=1, value=current.digest_after_hour,
            help="Bu saatten sonraki ilk kontrolde günlük özet bildirimi gönderilir.",
        )

        st.markdown("**Ağ sunucu modu**")
        server_port = st.number_input(
            "Port" + lock_note("server_port"),
            min_value=1024, max_value=65535, step=1, value=current.server_port,
            help="run_server.py bu portu dinler.",
        )

        if st.form_submit_button("Ayarları kaydet", type="primary"):
            settings_module.save_settings(settings_module.Settings(
                business_name=business_name.strip() or settings_module.DEFAULT_BUSINESS_NAME,
                currency=currency.strip() or settings_module.DEFAULT_CURRENCY,
                owner_name=owner_name.strip(),
                reminder_lead_minutes=int(reminder_lead_minutes),
                digest_after_hour=int(digest_after_hour),
                server_port=int(server_port),
            ))
            st.success("Ayarlar kaydedildi. Başlık ve etiketler yenilendi.")
            st.rerun()

    st.divider()
    st.markdown("**Veri**")
    st.caption(f"Veritabanı: `{db_path}`")
    if st.button("📦 Şimdi yedek al", key="settings_backup"):
        try:
            dest = db.backup_database(db_path)
            st.success(f"Yedek alındı: `{dest}`")
        except FileNotFoundError:
            st.error("Veritabanı bulunamadı.")


# ============================================================================
# Gezinme (sol panel) + hızlı işlemler (altta sabit) + veritabanı
# ============================================================================

db_path = config.resolve_db_path()  # varsayılan konum; gerekirse ISYONETIM_DB_PATH ortam değişkeniyle değiştirilebilir

conn = db.connect(db_path)
db.run_migrations(conn)  # yoksa oluşturur, varsa no-op

pg = st.navigation([
    st.Page(page_overview, title="Genel Bakış", icon=":material/space_dashboard:", default=True),
    st.Page(page_calendar, title="Takvim", icon=":material/calendar_month:"),
    st.Page(page_projects, title="Proje & Görev", icon=":material/checklist:"),
    st.Page(page_meetings, title="Toplantı & Aksiyon", icon=":material/groups:"),
    st.Page(page_ecommerce, title="E-ticaret", icon=":material/storefront:"),
    st.Page(page_settings, title="Ayarlar", icon=":material/settings:"),
])

with st.sidebar:
    with st.form("quick_add_form", clear_on_submit=True, border=False):
        quick_title = st.text_input(
            "Hızlı ekle", placeholder="⚡ Bir şey yaz, Enter'a bas...", label_visibility="collapsed",
        )
        if st.form_submit_button("Ekle", icon="➕", type="primary", width="stretch") and quick_title.strip():
            inbox_id = get_or_create_inbox_project(conn)
            project_model.create_task(conn, inbox_id, quick_title.strip(), priority_bucket="today")
            st.toast(f"Eklendi: {quick_title.strip()}", icon="⚡")
            st.rerun()

    agenda = build_agenda_lists(conn)

    def _agenda_list(items: list[dict]) -> None:
        for item in items:
            st.markdown(
                f"<div style='font-size:0.82rem;line-height:1.3;margin-bottom:6px;'>"
                f"{item['etiket']}<br><span style='opacity:0.55;font-size:0.72rem'>{item['tarih']}</span></div>",
                unsafe_allow_html=True,
            )

    if agenda["upcoming"]:
        with st.expander(f"🔜 Yaklaşan ({len(agenda['upcoming'])})"):
            _agenda_list(agenda["upcoming"])

    if agenda["overdue"]:
        with st.expander(f"⏰ Geçen ({len(agenda['overdue'])})"):
            _agenda_list(agenda["overdue"])

    with st.container(key="settings_footer"):
        st.divider()
        st.subheader("⚙️ Hızlı işlemler")
        if st.button("Yenile", icon="🔄", width="stretch"):
            st.rerun()
        if st.button("Şimdi yedek al", icon="📦", width="stretch"):
            try:
                backup_path = db.backup_database(db_path)
                st.toast(f"Yedek alındı: {backup_path.name}", icon="📦")
            except FileNotFoundError:
                st.toast("Veritabanı bulunamadı.", icon="⚠️")

if "startup_notified" not in st.session_state:
    st.session_state.startup_notified = True
    startup_summary = build_today_summary(conn)
    st.toast(format_today_digest(startup_summary), icon="📋")
    if startup_summary["overdue_actions"]:
        st.toast(f"⚠️ {len(startup_summary['overdue_actions'])} süresi geçmiş aksiyon var", icon="⚠️")
    upcoming_meeting = meeting_model.get_next_upcoming_meeting(conn)
    if upcoming_meeting:
        when = f"{upcoming_meeting.meeting_date} {upcoming_meeting.meeting_time}"
        st.toast(f"Yaklaşan toplantı: {upcoming_meeting.title} ({when})", icon="📅")

st.title(SETTINGS.panel_title)
st.caption(f"Kaynak: `{db_path}`")

pg.run()

conn.close()
