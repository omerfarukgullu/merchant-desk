"""Panelin açılış dumanı testi (streamlit AppTest ile).

Panel en büyük dosya ve en çok elle denenen parça; en azından hatasız
açıldığını, başlık ve tutar etiketlerinin Ayarlar'dan geldiğini otomatik
doğrulamak istiyoruz. Sayfa sayfa etkileşim testi değil.
"""

from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "isyonetim" / "dashboard" / "app.py"


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Boş, geçici bir veritabanına bağlı panel örneği."""
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("ISYONETIM_DB_PATH", str(tmp_path / "panel.db"))
    monkeypatch.setattr(
        "isyonetim.config.SETTINGS_PATH", tmp_path / "settings.json", raising=False
    )
    return AppTest.from_file(str(APP), default_timeout=120)


def test_dashboard_opens_without_error_on_empty_database(app):
    app.run()

    assert not app.exception
    assert app.title[0].value.endswith("İş Yönetim Paneli")


def test_title_follows_business_name_setting(app, monkeypatch):
    monkeypatch.setenv("ISYONETIM_BUSINESS_NAME", "Kahve Dükkanı")

    app.run()

    assert not app.exception
    assert app.title[0].value.startswith("Kahve Dükkanı")


def test_money_labels_follow_currency_setting(app, monkeypatch):
    monkeypatch.setenv("ISYONETIM_CURRENCY", "EUR")

    app.run()

    assert not app.exception
    labels = [m.label for m in app.metric]
    assert "Bu hafta ciro (EUR)" in labels
    assert not any("(TL)" in label for label in labels)


def test_empty_database_shows_zero_metrics(app):
    app.run()

    values = {m.label: m.value for m in app.metric}
    assert values["Bugün yapılacak görev"] == "0"
    assert values["Süresi geçmiş aksiyon"] == "0"
