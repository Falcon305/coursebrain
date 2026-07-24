from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .notes import Chunk

EMBED_MODEL = "minishlab/potion-base-8M"
EMBED_DIM = 256
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


# --- vectors: same file as the keyword index, so there is nothing to keep in sync ---

def vectors_available() -> bool:
    try:
        import model2vec  # noqa: F401
        import sqlite_vec  # noqa: F401
    except ImportError:
        return False
    return hasattr(sqlite3.Connection, "enable_load_extension")


def _load_vec(conn: sqlite3.Connection) -> bool:
    if not vectors_available():
        return False
    import sqlite_vec

    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except (AttributeError, sqlite3.OperationalError):
        return False


def _embedder() -> Any:
    if not hasattr(_embedder, "_model"):
        # keep the hub's progress bars and token warnings out of CLI output
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        from model2vec import StaticModel

        _embedder._model = StaticModel.from_pretrained(EMBED_MODEL)  # type: ignore[attr-defined]
    return _embedder._model  # type: ignore[attr-defined]


def embed(texts: list[str]) -> list[list[float]]:
    vectors = _embedder().encode(texts)
    out = []
    for v in vectors:
        norm = float((v * v).sum()) ** 0.5 or 1.0
        out.append([float(x) / norm for x in v])
    return out


def _connect(db_path: Path) -> tuple[sqlite3.Connection, bool]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, _load_vec(conn)


def build_index(db_path: Path, chunks: Iterable[Chunk], use_vectors: bool = True) -> tuple[int, int]:
    chunks = list(chunks)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn, has_vec = _connect(db_path)
    embedded = 0
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM chunks")
        for chunk in chunks:
            conn.execute(
                "INSERT INTO chunks (text, heading, title, course, episode, video_id, "
                "note_path, timestamp, layer) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    chunk.text, chunk.heading, chunk.title, chunk.course, str(chunk.episode),
                    chunk.video_id, chunk.note_path,
                    "" if chunk.timestamp is None else str(chunk.timestamp), chunk.layer,
                ),
            )

        if has_vec and use_vectors and chunks:
            import sqlite_vec

            conn.execute("DROP TABLE IF EXISTS vec_chunks")
            conn.execute(
                f"CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[{EMBED_DIM}])"
            )
            rowids = [r[0] for r in conn.execute("SELECT rowid FROM chunks ORDER BY rowid")]
            vectors = embed([f"{c.heading}\n{c.text}" for c in chunks])
            conn.executemany(
                "INSERT INTO vec_chunks(rowid, embedding) VALUES (?, ?)",
                [(rid, sqlite_vec.serialize_float32(v)) for rid, v in zip(rowids, vectors)],
            )
            embedded = len(vectors)
        conn.commit()
        return len(chunks), embedded
    finally:
        conn.close()


def keyword_search(db_path: Path, query: str, k: int, course: str | None = None) -> list[Chunk]:
    if not db_path.exists():
        return []
    match = fts_query(query)
    if not match:
        return []
    conn, _ = _connect(db_path)
    try:
        sql = "SELECT *, bm25(chunks, 1.0, 2.0, 1.5) AS rank FROM chunks WHERE chunks MATCH ?"
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


def vector_search(db_path: Path, query: str, k: int, course: str | None = None) -> list[Chunk]:
    if not db_path.exists() or not vectors_available():
        return []
    conn, has_vec = _connect(db_path)
    if not has_vec:
        conn.close()
        return []
    try:
        import sqlite_vec

        vector = sqlite_vec.serialize_float32(embed([query])[0])
        # over-fetch when filtering by course: the knn happens before the join
        limit = k * 5 if course else k
        rows = conn.execute(
            "SELECT c.*, v.distance FROM vec_chunks v JOIN chunks c ON c.rowid = v.rowid "
            "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
            (vector, limit),
        ).fetchall()
        out = [_row_to_chunk(r) for r in rows]
        if course:
            out = [c for c in out if c.course == course]
        return out[:k]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _key(chunk: Chunk) -> tuple[str, int, str]:
    return (chunk.course, chunk.episode, chunk.heading)


def reciprocal_rank_fusion(ranked: dict[str, list[Chunk]], k: int, rrf_k: int = RRF_K) -> list[Hit]:
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
    return [Hit(chunk=chunks[k2], score=s, sources=tuple(sources[k2])) for k2, s in ordered[:k]]


def search(
    index_db: Path,
    query: str,
    k: int = 5,
    course: str | None = None,
    pool: int = 20,
    use_vectors: bool = True,
) -> list[Hit]:
    ranked = {"keyword": keyword_search(index_db, query, pool, course)}
    if use_vectors:
        hits = vector_search(index_db, query, pool, course)
        if hits:
            ranked["vector"] = hits
    return reciprocal_rank_fusion(ranked, k)
