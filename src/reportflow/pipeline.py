from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from .models import ReportConfig, Snapshot
from .sources import load_source

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
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
        template = env.get_template("report.html")
        
        table_html = combined_df.to_html(
            classes="table table-striped table-hover", 
            index=False,
            border=0
        )
        
        html_content = template.render(
            title=config.title,
            snapshots=snapshots,
            records=combined_df.to_dict(orient="records"),
            table_html=table_html,
            generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        html_path.write_text(html_content, encoding="utf-8")
        results["html"] = str(html_path)
        
    return results
