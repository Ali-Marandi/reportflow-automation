from __future__ import annotations
import csv
import hashlib
import json
import logging
import time
from io import StringIO
from pathlib import Path
import requests
from .models import Snapshot, SourceConfig, SourceFormat, SourceType

logger = logging.getLogger(__name__)

def _compute_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def _parse_rows(payload: bytes, format: SourceFormat) -> list[dict[str, Any]]:
    text = payload.decode("utf-8-sig")
    if format == SourceFormat.CSV:
        return list(csv.DictReader(StringIO(text)))
    elif format == SourceFormat.JSON:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else parsed.get("data", [])
    raise ValueError(f"Unsupported format: {format}")

def load_source(config: SourceConfig, base_dir: Path) -> Snapshot:
    logger.info(f"Loading source: {config.name} ({config.type})")
    
    if config.type == SourceType.FILE:
        path = Path(config.path)
        if not path.is_absolute():
            path = base_dir / path
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        
        payload = path.read_bytes()
        source_id = str(path)
        
    elif config.type == SourceType.URL:
        error = None
        for attempt in range(config.retries + 1):
            try:
                response = requests.get(
                    str(config.url), 
                    timeout=config.timeout,
                    headers={"User-Agent": "ReportFlow/1.0.0"}
                )
                response.raise_for_status()
                payload = response.content
                source_id = str(config.url)
                break
            except requests.RequestException as e:
                error = e
                if attempt < config.retries:
                    wait = 0.5 * (2 ** attempt)
                    logger.warning(f"Attempt {attempt+1} failed for {config.name}. Retrying in {wait}s...")
                    time.sleep(wait)
        else:
            logger.error(f"Failed to retrieve data from {config.url} after {config.retries} retries")
            raise RuntimeError(f"Failed to retrieve {config.name}") from error
    
    rows = _parse_rows(payload, config.format)
    return Snapshot(
        name=config.name,
        source=source_id,
        sha256=_compute_sha256(payload),
        rows=rows
    )
