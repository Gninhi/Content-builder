import os
from pathlib import Path
from typing import Dict, Any
import json


class LocalStorageConnector:
    """
    Local filesystem storage connector mimicking object storage (S3 / Supabase Storage).
    """

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_text(self, path: str, content: str) -> str:
        target_path = self.base_dir / path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return str(target_path)

    def save_json(self, path: str, data: Dict[str, Any]) -> str:
        return self.save_text(path, json.dumps(data, indent=2, ensure_ascii=False))

    def read_text(self, path: str) -> str:
        target_path = self.base_dir / path
        if not target_path.exists():
            return ""
        return target_path.read_text(encoding="utf-8")
