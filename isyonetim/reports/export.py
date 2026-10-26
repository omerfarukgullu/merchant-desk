"""Basit CSV dışa aktarım yardımcıları.

Her liste/rapor komutu, dataclass nesnelerinden oluşan bir listeyi
buradaki export_rows fonksiyonuna vererek --csv <dosya> seçeneğini
destekler.
"""

import csv
import dataclasses
from pathlib import Path
from typing import Any


def _to_dict(row: Any) -> dict:
    if dataclasses.is_dataclass(row):
        return dataclasses.asdict(row)
    if isinstance(row, dict):
        return row
    raise TypeError(f"CSV'ye aktarılamayan satır tipi: {type(row)!r}")


def export_rows(rows: list[Any], path: str | Path) -> Path:
    out_path = Path(path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dict_rows = [_to_dict(r) for r in rows]
    fieldnames = list(dict_rows[0].keys()) if dict_rows else []
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_rows)
    return out_path
