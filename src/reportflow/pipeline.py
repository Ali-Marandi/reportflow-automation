from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .models import ReportConfig, Snapshot
from .sources import load_source
from .branding import BrandingConfig, build_template_context, get_jinja_env

logger = logging.getLogger(__name__)

def run_pipeline(config_path: str | Path, output_dir: str | Path) -> dict[str, str]:
    config_file = Path(config_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load and validate config
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        config = ReportConfig(**config_dict)
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    # Collection
    snapshots: list[Snapshot] = []
    for source_cfg in config.sources:
        try:
            snapshots.append(load_source(source_cfg, config_file.parent))
        except Exception as e:
            logger.error(f"Failed to load source {source_cfg.name}: {e}")
            # In commercial grade, we might continue or fail based on policy
            raise
    
    # Normalization using Pandas
    all_records = []
    for s in snapshots:
        df = pd.DataFrame(s.rows)
        df['source_name'] = s.name
        all_records.append(df)
    
    combined_df = pd.concat(all_records, ignore_index=True)
    
    # Clean numeric columns
    for col in combined_df.columns:
        if combined_df[col].dtype == 'object':
            try:
                # Try to convert to numeric, handling commas and strings
                temp = combined_df[col].astype(str).str.replace(',', '').str.strip()
                combined_df[col] = pd.to_numeric(temp)
            except (ValueError, TypeError):
                pass
    
    results = {}
    
    # Export JSON
    if "json" in config.output_formats:
        json_path = output_path / "report.json"
        report_data = {
            "title": config.title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": combined_df.to_dict(orient="records"),
            "provenance": [s.model_dump() for s in snapshots]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        results["json"] = str(json_path)
        
    # Export CSV
    if "csv" in config.output_formats:
        csv_path = output_path / "report.csv"
        combined_df.to_csv(csv_path, index=False)
        results["csv"] = str(csv_path)
        
    # Export HTML
    if "html" in config.output_formats:
        html_path = output_path / "report.html"

        # Build branding config (merge user overrides with defaults)
        brand_data = config.branding or {}
        brand = BrandingConfig(**brand_data)
        jinja_env, template_name = get_jinja_env(brand)
        template = jinja_env.get_template(template_name)

        table_html = combined_df.to_html(
            classes="table table-striped table-hover",
            index=False,
            border=0,
        )

        base_ctx = {
            "title": config.title,
            "snapshots": snapshots,
            "records": combined_df.to_dict(orient="records"),
            "table_html": table_html,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        ctx = build_template_context(base_ctx, brand)
        html_content = template.render(**ctx)
        html_path.write_text(html_content, encoding="utf-8")
        results["html"] = str(html_path)
        
    return results
