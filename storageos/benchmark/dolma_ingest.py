"""Dolma bulk ingest — optimized for speed.

Strategy:
  1. WAL + sync=OFF for bulk writes
  2. No FTS triggers during load — insert into passages_fts manually in bulk
  3. Rebuild FTS index once at end
  4. Skip unnecessary tables (versions, manifests, nodes) — only what FTS needs
  5. Large batches via executemany
"""
import gzip
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\raw")
INDEX_PATH = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\prepared\doc_index.jsonl")
DB_PATH = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\dolma.db")

PASSAGE_MAX_CHARS = 2000
BATCH_SIZE = 200000

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS spaces (
    space_id TEXT PRIMARY KEY, name TEXT NOT NULL,
    root_path TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY, space_id TEXT NOT NULL,
    absolute_path TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
    extension TEXT NOT NULL, size INTEGER NOT NULL, mtime REAL NOT NULL,
    content_hash TEXT, source_type TEXT NOT NULL,
    first_seen REAL NOT NULL, last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS passages (
    passage_id TEXT PRIMARY KEY, resource_id TEXT NOT NULL,
    version_id TEXT, node_id TEXT,
    text TEXT NOT NULL, start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL
);
"""


def split_text(text, max_chars):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars])
                current = ""
            else:
                current = para
        else:
            current = current + "\n\n" + para if current else para
    if current:
        chunks.append(current)
    return chunks


def build_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.executescript(SCHEMA_SQL)

    # WAL mode + performance pragmas
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-256000")  # 256MB cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
    conn.execute("PRAGMA page_size=8192")

    # Create space
    space_id = "dolma-v1_6"
    conn.execute("INSERT OR IGNORE INTO spaces VALUES (?,?,?,?)",
                 (space_id, "dolma-v1_6", str(RAW_DIR), time.time()))
    conn.commit()

    # Load index
    entries = []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))
    print(f"Index: {len(entries):,} documents")

    by_shard = {}
    for e in entries:
        by_shard.setdefault(e["shard"], []).append(e)

    t0 = time.time()
    resource_count = 0
    passage_count = 0

    res_batch = []
    pass_batch = []

    for shard_name, shard_entries in sorted(by_shard.items()):
        shard_path = RAW_DIR / shard_name
        print(f"\n{shard_name}: {len(shard_entries)} docs...", end=" ", flush=True)

        shard_entries.sort(key=lambda e: e["line_num"])
        entry_by_line = {e["line_num"]: e for e in shard_entries}

        shard_t0 = time.time()
        shard_docs = 0

        with gzip.open(shard_path, "rt", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if line_num not in entry_by_line:
                    continue

                entry = entry_by_line[line_num]
                rec = json.loads(line)
                doc_id = entry["doc_id"]
                text = rec.get("text", "")
                text_bytes = len(text.encode("utf-8"))

                resource_id = f"r-{doc_id}"
                abs_path = f"dolma://{shard_name}/{doc_id}"

                res_batch.append((
                    resource_id, space_id, abs_path,
                    f"{doc_id[:16]}.txt", ".txt",
                    text_bytes, 0, doc_id, "text", 0, 0
                ))

                chunks = split_text(text, PASSAGE_MAX_CHARS)
                for i, chunk in enumerate(chunks):
                    start = i * PASSAGE_MAX_CHARS
                    end = start + len(chunk)
                    pass_batch.append((
                        f"p-{doc_id}-{i:04d}",
                        resource_id, None, None,
                        chunk, start, end
                    ))
                    passage_count += 1

                resource_count += 1
                shard_docs += 1

                if len(res_batch) >= BATCH_SIZE:
                    _flush(conn, res_batch, pass_batch)
                    res_batch, pass_batch = [], []
                    elapsed = time.time() - t0
                    rate = resource_count / elapsed if elapsed > 0 else 0
                    print(f"{resource_count:,} ({rate:,.0f}/s)...", end=" ", flush=True)

        # Flush remaining for this shard
        if res_batch:
            _flush(conn, res_batch, pass_batch)
            res_batch, pass_batch = [], []

        shard_elapsed = time.time() - shard_t0
        print(f"done ({shard_docs:,} in {shard_elapsed:.1f}s)")

    # Final commit
    conn.commit()

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"BULK INSERT COMPLETE ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"Resources: {resource_count:,}")
    print(f"Passages:  {passage_count:,}")
    print(f"Rate:      {resource_count/elapsed:,.0f} docs/sec, {passage_count/elapsed:,.0f} passages/sec")

    # Build FTS index
    # detail=none skips position tracking — much faster for bulk load
    print(f"\nBuilding FTS index (detail=none)...", end=" ", flush=True)
    t1 = time.time()

    conn.execute("DROP TABLE IF EXISTS passages_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            passage_id, text,
            detail=none
        )
    """)
    conn.execute("""
        INSERT INTO passages_fts(passage_id, text)
        SELECT passage_id, text FROM passages
    """)
    conn.commit()
    fts_elapsed = time.time() - t1
    print(f"done ({fts_elapsed:.1f}s)")

    db_size = DB_PATH.stat().st_size / (1024**2)
    print(f"\nDB size: {db_size:.1f} MB")

    # Verify
    print(f"\nVerifying...", end=" ", flush=True)
    db_fts = conn.execute("SELECT COUNT(*) FROM passages_fts").fetchone()[0]
    db_pass = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    db_res = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    print(f"FTS rows: {db_fts:,}")
    print(f"Passage rows: {db_pass:,}")
    print(f"Resource rows: {db_res:,}")

    # CRITICAL: Conservation checks — fail hard on mismatch
    errors = []
    if db_res != resource_count:
        errors.append(f"Resource conservation: batched={resource_count:,}, stored={db_res:,}, lost={resource_count - db_res:,}")
    if db_pass != passage_count:
        errors.append(f"Passage conservation: batched={passage_count:,}, stored={db_pass:,}, lost={passage_count - db_pass:,}")
    if db_fts != db_pass:
        errors.append(f"FTS conservation: passages={db_pass:,}, fts={db_fts:,}, delta={db_pass - db_fts:,}")

    if errors:
        print(f"\n{'='*60}")
        print(f"INTEGRITY VIOLATION — INGESTION ABORTED")
        print(f"{'='*60}")
        for e in errors:
            print(f"  FAIL: {e}")
        print(f"\nData may be corrupted. Do NOT use this DB for benchmarks.")
        conn.close()
        raise RuntimeError("Ingestion conservation check failed: " + "; ".join(errors))

    print(f"\nConservation checks PASSED")

    # Test FTS search
    t2 = time.time()
    results = conn.execute(
        "SELECT passage_id FROM passages_fts WHERE passages_fts MATCH '\"science\"' LIMIT 5"
    ).fetchall()
    search_elapsed = (time.time() - t2) * 1000
    print(f"FTS test query: {len(results)} results in {search_elapsed:.1f}ms")
    for r in results:
        print(f"  {r[0]}")

    conn.close()


def _flush(conn, res_batch, pass_batch):
    conn.executemany(
        "INSERT OR IGNORE INTO resources VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        res_batch
    )
    conn.executemany(
        "INSERT OR IGNORE INTO passages VALUES (?,?,?,?,?,?,?)",
        pass_batch
    )
    conn.commit()


if __name__ == "__main__":
    build_db()
