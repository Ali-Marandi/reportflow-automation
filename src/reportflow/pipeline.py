"""Config-driven collection, normalization and publication pipeline."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from .sources import Snapshot, load_file, load_url


def _collect(config: dict, base: Path) -> list[Snapshot]:
    snapshots = []
    for item in config["sources"]:
        source_type = item["type"]
        kind = item.get("format", "json")
        if source_type == "file":
            path = Path(item["path"])
            if not path.is_absolute():
                path = base / path
            snapshots.append(load_file(item["name"], path, kind))
        elif source_type == "url":
            snapshots.append(
                load_url(
                    item["name"],
                    item["url"],
                    kind,
                    timeout=float(item.get("timeout", 15)),
                    retries=int(item.get("retries", 2)),
                )
            )
        else:
            raise ValueError(f"unknown source type: {source_type}")
    return snapshots


def _normalize(snapshots: list[Snapshot]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for snapshot in snapshots:
        for row in snapshot.rows:
            record = {"source": snapshot.name, **row}
            for key, value in list(record.items()):
                if isinstance(value, str):
                    stripped = value.strip().replace(",", "")
                    try:
                        record[key] = float(stripped)
                    except ValueError:
                        record[key] = value.strip()
            records.append(record)
    return records


def _write_csv(records: list[dict[str, object]], path: Path) -> None:
    fields = sorted({key for record in records for key in record})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def _write_html(config: dict, records: list[dict[str, object]], snapshots: list[Snapshot], path: Path) -> None:
    fields = sorted({key for record in records for key in record})
    head = "".join(f"<th>{escape(field)}</th>" for field in fields)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(record.get(field, '')))}</td>" for field in fields) + "</tr>"
        for record in records
    )
    provenance = "".join(
        f"<li><strong>{escape(item.name)}</strong> — {escape(item.source)}"
        f"<br><code>{item.sha256}</code> · {escape(item.retrieved_at)}</li>"
        for item in snapshots
    )
    title = escape(config.get("title", "Automated report"))
    html = f"""<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{font:14px system-ui;background:#f5f7fa;color:#17202a;margin:0}}main{{max-width:1300px;margin:auto;padding:32px}}
.card{{background:white;padding:20px;border-radius:14px;margin:18px 0;box-shadow:0 4px 20px #17202a12}}
.table{{overflow:auto}}table{{border-collapse:collapse;width:100%;white-space:nowrap}}
th,td{{padding:10px;border-bottom:1px solid #e5e9ef;text-align:left}}th{{background:#162d4d;color:white}}
code{{font-size:11px;word-break:break-all}}</style><main><h1>{title}</h1>
<div class="card"><strong>{len(records)}</strong> normalized records from <strong>{len(snapshots)}</strong> sources.</div>
<div class="card table"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h2>Data provenance</h2><ul>{provenance}</ul></div></main></html>"""
    path.write_text(html, encoding="utf-8")


def run_pipeline(config_path: str | Path, output_dir: str | Path) -> dict[str, str]:
    config_file = Path(config_path)
    config = json.loads(config_file.read_text(encoding="utf-8"))
    if not config.get("sources"):
        raise ValueError("configuration requires at least one source")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    snapshots = _collect(config, config_file.parent)
    records = _normalize(snapshots)
    if not records:
        raise ValueError("sources returned no records")
    (output / "report.json").write_text(
        json.dumps(
            {"title": config.get("title"), "records": records, "provenance": [asdict(item) for item in snapshots]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(records, output / "report.csv")
    _write_html(config, records, snapshots, output / "report.html")
    return {name: str(output / name) for name in ("report.json", "report.csv", "report.html")}
