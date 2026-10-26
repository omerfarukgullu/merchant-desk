"""isyonetim/settings.py: kaynak önceliği, bozuk değerler, biçimlendirme."""

import json

from isyonetim import settings as settings_module


def test_defaults_when_nothing_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", tmp_path / "yok.json")

    cfg = settings_module.load_settings()

    assert cfg.business_name == settings_module.DEFAULT_BUSINESS_NAME
    assert cfg.currency == settings_module.DEFAULT_CURRENCY
    assert cfg.reminder_lead_minutes == settings_module.DEFAULT_REMINDER_LEAD_MINUTES
    assert cfg.owner_name == ""


def test_settings_file_is_read(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"business_name": "Kahve Dükkanı", "currency": "EUR", "server_port": 9000}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", path)

    cfg = settings_module.load_settings()

    assert cfg.business_name == "Kahve Dükkanı"
    assert cfg.currency == "EUR"
    assert cfg.server_port == 9000


def test_env_var_beats_settings_file(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"currency": "EUR"}), encoding="utf-8")
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", path)
    monkeypatch.setenv("ISYONETIM_CURRENCY", "USD")

    assert settings_module.load_settings().currency == "USD"
    assert settings_module.env_overrides() == {"currency"}


def test_corrupt_settings_file_falls_back_to_defaults(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ bu gecerli json degil", encoding="utf-8")
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", path)

    cfg = settings_module.load_settings()

    assert cfg.currency == settings_module.DEFAULT_CURRENCY


def test_unknown_and_invalid_values_are_ignored(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"bilinmeyen_alan": 1, "reminder_lead_minutes": "onbes", "currency": "GBP"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", path)

    cfg = settings_module.load_settings()

    assert cfg.currency == "GBP"
    # Sayıya çevrilemeyen değer varsayılanda kalmalı, çökmemeli
    assert cfg.reminder_lead_minutes == settings_module.DEFAULT_REMINDER_LEAD_MINUTES
    assert not hasattr(cfg, "bilinmeyen_alan")


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    path = tmp_path / "data" / "settings.json"
    monkeypatch.setattr(settings_module.config, "SETTINGS_PATH", path)

    settings_module.save_settings(
        settings_module.Settings(business_name="Atölye", currency="£", owner_name="Yönetici")
    )

    cfg = settings_module.load_settings()
    assert cfg.business_name == "Atölye"
    assert cfg.currency == "£"
    assert cfg.owner_name == "Yönetici"
    # Türkçe karakterler okunabilir biçimde yazılmalı (ensure_ascii=False)
    assert "Atölye" in path.read_text(encoding="utf-8")


def test_money_and_label_formatting():
    cfg = settings_module.Settings(currency="EUR", business_name="Acme")

    assert cfg.money(1234.56) == "1,235 EUR"
    assert cfg.money(1234.56, decimals=2) == "1,234.56 EUR"
    assert cfg.money(None) == "—"
    assert cfg.money_label("Ciro") == "Ciro (EUR)"
    assert cfg.panel_title.startswith("Acme")
