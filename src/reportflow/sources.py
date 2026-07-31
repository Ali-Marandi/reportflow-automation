"""Source adapters with provenance, checksums, retries and timeouts."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Snapshot:
    name: str
    source: str
    retrieved_at: str
    sha256: str
    rows: list[dict[str, object]]


def _snapshot(name: str, source: str, payload: bytes, rows: list[dict[str, object]]) -> Snapshot:
    return Snapshot(
        name=name,
        source=source,
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sha256=hashlib.sha256(payload).hexdigest(),
        rows=rows,
    )


def load_file(name: str, path: str | Path, kind: str) -> Snapshot:
    source = Path(path)
    payload = source.read_bytes()
    text = payload.decode("utf-8-sig")
    if kind == "csv":
        rows = list(csv.DictReader(StringIO(text)))
    elif kind == "json":
        parsed = json.loads(text)
        rows = parsed if isinstance(parsed, list) else parsed.get("data", [])
    else:
        raise ValueError(f"unsupported file kind: {kind}")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("source must produce a list of objects")
    return _snapshot(name, str(source), payload, rows)


def load_url(name: str, url: str, kind: str, timeout: float = 15, retries: int = 2) -> Snapshot:
    error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "ReportFlow/0.1"})
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            text = payload.decode("utf-8-sig")
            if kind == "csv":
                rows = list(csv.DictReader(StringIO(text)))
            elif kind == "json":
                parsed = json.loads(text)
                rows = parsed if isinstance(parsed, list) else parsed.get("data", [])
            else:
                raise ValueError(f"unsupported URL kind: {kind}")
            return _snapshot(name, url, payload, rows)
        except Exception as exc:  # network errors are retried and then surfaced
            error = exc
            if attempt < retries:
                time.sleep(0.25 * 2**attempt)
    raise RuntimeError(f"failed to retrieve {url}") from error
