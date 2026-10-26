"""CLI komut yüzeyi (typer) — uçtan uca, geçici bir veritabanı dosyasıyla."""

import pytest
from typer.testing import CliRunner

from isyonetim.cli.main import app

runner = CliRunner()


@pytest.fixture
def run(db_file):
    """CLI'yi geçici veritabanına yönlendirerek çağıran yardımcı."""
    def _run(*args, expect_ok=True):
        result = runner.invoke(app, ["--db", str(db_file), *args])
        if expect_ok:
            assert result.exit_code == 0, f"{args} -> {result.exit_code}\n{result.output}"
        return result
    return _run


def test_init_creates_database(run, db_file):
    result = run("init")

    assert db_file.exists()
    assert "0001_init.sql" in result.output


def test_init_is_idempotent(run):
    run("init")
    result = run("init")

    assert "güncel" in result.output


def test_project_and_task_lifecycle(run):
    run("init")
    run("project", "add", "Ürün Satışı", "--goal", "Aylık 100 sipariş")

    assert "Ürün Satışı" in run("project", "list").output

    run("project", "add-task", "Ürün Satışı", "Stok sayımı", "-p", "today")
    assert "Stok sayımı" in run("project", "list-tasks").output

    run("project", "set-task-status", "1", "completed")
    assert "completed" in run("project", "list-tasks").output
    # Tamamlanan görev --open-only ile gizlenmeli
    assert "Stok sayımı" not in run("project", "list-tasks", "--open-only").output


def test_project_can_be_referenced_by_id_or_name(run):
    run("init")
    run("project", "add", "Proje")

    assert run("project", "add-task", "1", "Id ile").exit_code == 0
    assert run("project", "add-task", "Proje", "İsim ile").exit_code == 0


def test_unknown_project_exits_with_error(run):
    run("init")

    result = run("project", "add-task", "Olmayan Proje", "Görev", expect_ok=False)

    assert result.exit_code == 1


def test_phase_commands(run):
    run("init")
    run("project", "add", "Proje")
    run("project", "add-phase", "Proje", "Tedarikçi görüşmeleri", "--order", "1")

    assert "Tedarikçi görüşmeleri" in run("project", "list-phases").output

    run("project", "set-phase-status", "1", "completed")
    assert "completed" in run("project", "list-phases").output


def test_meeting_and_action_lifecycle(run):
    run("init")
    run("meeting", "add", "Tedarikçi görüşmesi", "--date", "2026-05-04", "--time", "14:30",
        "-t", "supplier")

    assert "14:30" in run("meeting", "list").output

    run("meeting", "add-action", "1", "Teklif iste", "--owner", "Yönetici", "--due", "2026-05-10")
    actions = run("meeting", "list-actions").output
    assert "Teklif iste" in actions

    run("meeting", "close-action", "1")
    assert "done" in run("meeting", "list-actions").output
    assert "Teklif iste" not in run("meeting", "list-actions", "--open-only").output


def test_ecommerce_flow_and_price_comparison(run):
    run("init")
    run("product", "add", "Ürün A", "--sku", "URUN-A", "--cost", "420")
    run("channel", "add", "Pazar Yeri", "-t", "marketplace")
    run("listing", "set", "Ürün A", "Pazar Yeri", "--price", "559")
    run("price", "add", "Ürün A", "559", "--channel", "Pazar Yeri")
    run("price", "add", "Ürün A", "545", "--competitor", "Rakip 1")
    run("sale", "add", "Ürün A", "Pazar Yeri", "--qty", "2", "--price", "559", "--date", "2026-05-04")

    assert "Ürün A" in run("product", "list").output
    assert "Pazar Yeri" in run("channel", "list").output

    comparison = run("price", "compare", "Ürün A").output
    assert "559" in comparison
    assert "Rakip 1" in comparison

    assert "559" in run("sale", "list").output


def test_price_add_requires_channel_or_competitor(run):
    run("init")
    run("product", "add", "Ürün")

    result = run("price", "add", "Ürün", "100", expect_ok=False)

    assert result.exit_code == 1


def test_today_and_weekly_reports_run_on_empty_db(run):
    run("init")

    assert "Bugün" in run("today").output
    assert "Haftalık özet" in run("weekly-summary").output


def test_weekly_summary_uses_configured_currency(run, monkeypatch):
    monkeypatch.setenv("ISYONETIM_CURRENCY", "EUR")
    run("init")

    assert "EUR" in run("weekly-summary").output


def test_csv_export_option(run, tmp_path):
    run("init")
    run("project", "add", "Proje")
    out = tmp_path / "projeler.csv"

    run("project", "list", "--csv", str(out))

    assert out.exists()
    assert "Proje" in out.read_text(encoding="utf-8-sig")


def test_backup_command(run, db_file, tmp_path):
    run("init")
    out_dir = tmp_path / "yedek"

    result = run("backup", "--out-dir", str(out_dir))

    assert "Yedek alındı" in result.output
    assert list(out_dir.glob("*.db"))


def test_backup_without_database_fails_clearly(run, tmp_path):
    result = run("backup", "--out-dir", str(tmp_path), expect_ok=False)

    assert result.exit_code == 1
