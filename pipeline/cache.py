from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def content_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class Cache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.hits = 0
        self.misses = 0

    def key(self, stage: str, version: str, inputs: Any) -> str:
        return content_hash({"stage": stage, "version": version, "inputs": inputs})

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            self.misses += 1
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink(missing_ok=True)
            self.misses += 1
            return None
        self.hits += 1
        return payload["value"]

    def put(self, key: str, value: Any) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"key": key, "value": value}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)

    def clear(self) -> int:
        removed = 0
        for path in self.root.rglob("*.json"):
            path.unlink()
            removed += 1
        return removed

    @property
    def stats(self) -> str:
        total = self.hits + self.misses
        pct = (100 * self.hits / total) if total else 0.0
        return f"cache: {self.hits} hit / {self.misses} miss ({pct:.0f}%)"
