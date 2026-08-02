from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

class SourceFormat(str, Enum):
    JSON = "json"
    CSV = "csv"

class SourceType(str, Enum):
    FILE = "file"
    URL = "url"

class SourceConfig(BaseModel):
    name: str = Field(..., description="Unique name for the data source")
    type: SourceType = Field(..., description="Type of source: file or url")
    format: SourceFormat = Field(SourceFormat.JSON, description="Data format: json or csv")
    path: Optional[str] = Field(None, description="Path to the file (required if type is file)")
    url: Optional[str] = Field(None, description="URL to the data (required if type is url)")
    timeout: float = Field(15.0, ge=1.0)
    retries: int = Field(2, ge=0)

    @model_validator(mode="after")
    def check_source_fields(self) -> "SourceConfig":
        if self.type == SourceType.FILE and not self.path:
            raise ValueError("path is required for file source type")
        if self.type == SourceType.URL and not self.url:
            raise ValueError("url is required for url source type")
        return self

class ReportConfig(BaseModel):
    title: str = Field("Automated Financial Report", description="Title of the generated report")
    sources: List[SourceConfig] = Field(..., min_length=1)
    output_formats: List[str] = Field(["html", "csv", "json"], description="Desired output formats")
    branding: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional branding / theme overrides (see BrandingConfig for all keys)",
    )

class Snapshot(BaseModel):
    name: str
    source: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sha256: str
    rows: List[Dict[str, Any]]
