"""config.toml'un kapsamadığı ince görsel efektler (ışıma, ızgara dokusu,
monospace okuma) tek bir CSS bloğu olarak buradan enjekte edilir.

Seçiciler render edilmiş DOM'a bakılarak yazıldı (Streamlit 1.61). Üst bir
sürümde değişirlerse efekt kaybolur, sayfa bozulmaz.
"""

GLOW = "56, 189, 248"  # primaryColor (#38bdf8) rgb bileşenleri
TASK_TINT = "57, 135, 229"    # chartCategoricalColors slot 1 (mavi)
MEETING_TINT = "217, 89, 38"  # chartCategoricalColors slot 2 (turuncu)
ACTION_TINT = "213, 81, 129"  # chartCategoricalColors slot 5 (macenta)

CUSTOM_CSS = f"""
<style>
/* KPI değerleri: monospace + tabular rakam, sayılar hizalı dursun */
[data-testid="stMetricValue"] {{
    font-family: "Cascadia Code", "Consolas", "SF Mono", "Roboto Mono", monospace;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
}}
[data-testid="stMetricLabel"] {{
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-size: 0.72rem;
    opacity: 0.75;
}}

/* Ana içerik alanına ince nokta ızgarası - devre kartı hissi */
[data-testid="stMain"] {{
    background-image: radial-gradient(circle, rgba({GLOW}, 0.16) 1px, transparent 1px);
    background-size: 24px 24px;
}}

/* Birincil aksiyon butonlarında ("Ekle", "Kaydet" ...) hafif ışıma */
button[kind="primary"], button[data-testid^="stBaseButton-primary"] {{
    box-shadow: 0 0 0 1px rgba({GLOW}, 0.45), 0 0 14px rgba({GLOW}, 0.35);
    transition: box-shadow 0.15s ease;
}}
button[kind="primary"]:hover, button[data-testid^="stBaseButton-primary"]:hover {{
    box-shadow: 0 0 0 1px rgba({GLOW}, 0.7), 0 0 22px rgba({GLOW}, 0.55);
}}

/* Aktif sekmeye hafif ışıma (eski st.tabs kalıntısı - artık kullanılmıyor
   olsa da başka bir yerde sekme kullanılırsa zararsız) */
[data-testid="stTab"][aria-selected="true"] {{
    box-shadow: 0 2px 8px -1px rgba({GLOW}, 0.6);
    border-radius: 4px 4px 0 0;
}}

/* Sol panel: gezinme menüsü üstte, "settings_footer" konteyneri
   (⚙️ Ayarlar) flexbox ile en alta sabitlenir. */
[data-testid="stSidebarContent"] {{
    display: flex;
    flex-direction: column;
    min-height: 100%;
}}
.st-key-settings_footer {{
    margin-top: auto;
    padding-bottom: 0.5rem;
}}

/* Aktif gezinme öğesine hafif ışıma */
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    box-shadow: inset 3px 0 0 0 rgba({GLOW}, 0.9), 0 0 12px -2px rgba({GLOW}, 0.5);
}}

/* Takvim (Takvim sayfası) - düz, 7 sütunlu ay ızgarası */
.iy-cal {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    margin-top: 0.5rem;
}}
.iy-cal-weekday {{
    text-align: center;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.6;
    padding-bottom: 4px;
}}
.iy-cal-day {{
    min-height: 92px;
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 10px;
    padding: 6px;
}}
.iy-cal-day.outside {{
    border-color: transparent;
}}
.iy-cal-day.today {{
    border-color: rgba({GLOW}, 0.9);
    box-shadow: 0 0 10px -1px rgba({GLOW}, 0.45);
}}
.iy-cal-daynum {{
    font-family: "Cascadia Code", "Consolas", "SF Mono", "Roboto Mono", monospace;
    font-weight: 600;
    font-size: 0.8rem;
    opacity: 0.85;
    margin-bottom: 4px;
}}
.iy-cal-note {{
    font-size: 0.68rem;
    line-height: 1.5;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 1px 5px;
    border-radius: 5px;
    margin-bottom: 2px;
}}
.iy-cal-note-task {{ background: rgba({TASK_TINT}, 0.20); }}
.iy-cal-note-meeting {{ background: rgba({MEETING_TINT}, 0.20); }}
.iy-cal-note-action {{ background: rgba({ACTION_TINT}, 0.20); }}
.iy-cal-more {{
    font-size: 0.65rem;
    opacity: 0.6;
}}

/* İnce, aksan renkli kaydırma çubuğu */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: rgba({GLOW}, 0.35); border-radius: 8px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba({GLOW}, 0.55); }}
</style>
"""
