from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Prompt:
    text: str
    version: str


class _NullSpan:
    trace_id: str | None = None

    def update(self, **_: Any) -> None: ...
    def score(self, **_: Any) -> None: ...


class Observability:
    def __init__(self, enabled: bool = True) -> None:
        self._client: Any = None
        self.enabled = False
        if not enabled:
            return
        if not all(os.environ.get(k) for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")):
            return
        try:
            from langfuse import Langfuse
        except ImportError:
            return
        try:
            self._client = Langfuse(
                public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
                secret_key=os.environ["LANGFUSE_SECRET_KEY"],
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            self.enabled = True
        except Exception:
            self._client = None

    @contextmanager
    def span(self, name: str, **metadata: Any) -> Iterator[Any]:
        if not self.enabled:
            yield _NullSpan()
            return
        span = None
        try:
            span = self._client.start_span(name=name, metadata=metadata)
            yield span
        except Exception:
            yield _NullSpan()
        finally:
            try:
                if span is not None:
                    span.end()
            except Exception:
                pass

    def get_prompt(self, name: str, fallback: Path) -> Prompt:
        if self.enabled:
            try:
                p = self._client.get_prompt(name)
                return Prompt(text=p.prompt, version=f"lf{p.version}")
            except Exception:
                pass
        from .cache import content_hash

        text = fallback.read_text(encoding="utf-8")
        return Prompt(text=text, version=f"local{content_hash(text)[:8]}")

    def flush(self) -> None:
        if self.enabled:
            with contextlib.suppress(Exception):
                self._client.flush()

    @property
    def status(self) -> str:
        return "langfuse: on" if self.enabled else "langfuse: off"
