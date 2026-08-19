from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class DiskConfig(BaseModel):
    name: str
    mountpoint: str
    device: Optional[str] = None


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8926
    api_token: str = Field(min_length=16)
    chia_root: str = "~/.chia/mainnet"
    refresh_seconds: int = Field(default=30, ge=10)
    activity_stale_seconds: int = Field(default=300, ge=60)
    allowed_origins: list[str] = []
    disks: list[DiskConfig] = []

    @property
    def root(self) -> Path:
        return Path(self.chia_root).expanduser()

    @classmethod
    def load(cls, path: str | Path) -> "Settings":
        raw: dict[str, Any] = yaml.safe_load(Path(path).read_text()) or {}
        return cls.model_validate(raw)
