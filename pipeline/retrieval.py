from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .notes import Chunk

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RRF_K = 60
WORD_RE = re.compile(r"[\w']+", re.UNICODE)

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
    text, heading, title,
    course UNINDEXED, episode UNINDEXED, video_id UNINDEXED,
    note_path UNINDEXED, timestamp UNINDEXED, layer UNINDEXED,
    tokenize='porter unicode61'
);
"""


@dataclass
class Hit:
    chunk: Chunk
    score: float
    sources: tuple[str, ...] = ()

    def cite(self) -> str:
        return f"{self.chunk.label} — {self.chunk.url}"


def fts_query(text: str) -> str:
    terms = [t for t in WORD_RE.findall(text) if len(t) > 1]
    return " OR ".join(f'"{t}"' for t in terms)


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    return Chunk(
        course=row["course"],
        episode=int(row["episode"] or 0),
        video_id=row["video_id"],
        note_path=row["note_path"],
        title=row["title"],
        heading=row["heading"],
        text=row["text"],
        timestamp=int(row["timestamp"]) if row["timestamp"] not in (None, "") else None,
        layer=row["layer"],
    )


def build_keyword_index(db_path: Path, chunks: Iterable[Chunk]) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM chunks")
        rows = [
            (
                c.text, c.heading, c.title, c.course, str(c.episode), c.video_id,
                c.note_path, "" if c.timestamp is None else str(c.timestamp), c.layer,
            )
            for c in chunks
        ]
        conn.executemany(
            "INSERT INTO chunks (text, heading, title, course, episode, video_id, "
            "note_path, timestamp, layer) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def keyword_search(db_path: Path, query: str, k: int, course: str | None = None) -> list[Chunk]:
    if not db_path.exists():
        return []
    match = fts_query(query)
    if not match:
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT *, bm25(chunks, 1.0, 2.0, 1.5) AS rank FROM chunks "
            "WHERE chunks MATCH ?"
        )
        params: list[Any] = [match]
        if course:
            sql += " AND course = ?"
            params.append(course)
        sql += " ORDER BY rank LIMIT ?"
        params.append(k)
        return [_row_to_chunk(r) for r in conn.execute(sql, params)]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _embedder() -> Any:
    from sentence_transformers import SentenceTransformer

    if not hasattr(_embedder, "_model"):
        _embedder._model = SentenceTransformer(EMBED_MODEL)  # type: ignore[attr-defined]
    return _embedder._model  # type: ignore[attr-defined]


def vectors_available() -> bool:
    try:
        import lancedb  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def build_vector_index(db_dir: Path, chunks: list[Chunk]) -> int:
    if not vectors_available() or not chunks:
        return 0
    import lancedb

    model = _embedder()
    texts = [f"{c.heading}\n{c.text}" for c in chunks]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    rows = [
        {
            "vector": vectors[i].tolist(),
            "text": c.text,
            "heading": c.heading,
            "title": c.title,
            "course": c.course,
            "episode": c.episode,
            "video_id": c.video_id,
            "note_path": c.note_path,
            "timestamp": -1 if c.timestamp is None else c.timestamp,
            "layer": c.layer,
        }
        for i, c in enumerate(chunks)
    ]
    db_dir.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(db_dir))
    db.create_table("chunks", data=rows, mode="overwrite")
    return len(rows)


def vector_search(db_dir: Path, query: str, k: int, course: str | None = None) -> list[Chunk]:
    if not vectors_available() or not db_dir.exists():
        return []
    import lancedb

    try:
        table = lancedb.connect(str(db_dir)).open_table("chunks")
    except Exception:
        return []
    vector = _embedder().encode([query], normalize_embeddings=True)[0].tolist()
    search = table.search(vector).limit(k)
    if course:
        search = search.where(f"course = '{course}'")
    out: list[Chunk] = []
    for row in search.to_list():
        out.append(
            Chunk(
                course=row["course"],
                episode=int(row["episode"]),
                video_id=row["video_id"],
                note_path=row["note_path"],
                title=row["title"],
                heading=row["heading"],
                text=row["text"],
                timestamp=None if row["timestamp"] < 0 else int(row["timestamp"]),
                layer=row["layer"],
            )
        )
    return out


def _key(chunk: Chunk) -> tuple[str, int, str]:
    return (chunk.course, chunk.episode, chunk.heading)


def reciprocal_rank_fusion(
    ranked: dict[str, list[Chunk]], k: int, rrf_k: int = RRF_K
) -> list[Hit]:
    scores: dict[tuple[str, int, str], float] = {}
    chunks: dict[tuple[str, int, str], Chunk] = {}
    sources: dict[tuple[str, int, str], list[str]] = {}

    for source, results in ranked.items():
        for rank, chunk in enumerate(results, start=1):
            key = _key(chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            chunks.setdefault(key, chunk)
            sources.setdefault(key, []).append(source)

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        Hit(chunk=chunks[key], score=score, sources=tuple(sources[key]))
        for key, score in ordered[:k]
    ]


def search(
    index_db: Path,
    lancedb_dir: Path,
    query: str,
    k: int = 5,
    course: str | None = None,
    pool: int = 20,
    use_vectors: bool = True,
) -> list[Hit]:
    ranked = {"keyword": keyword_search(index_db, query, pool, course)}
    if use_vectors and vectors_available():
        ranked["vector"] = vector_search(lancedb_dir, query, pool, course)
    return reciprocal_rank_fusion(ranked, k)
