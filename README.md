# StorageOS

A retrieval-aware information representation system that compiles document structure *before* retrieval, then uses that precompiled representation to reduce search work while preserving evidence quality.

StorageOS is a research project testing a single hypothesis:

> **Can a retrieval-aware representation, compiled before retrieval and before expensive semantic indexing, reduce retrieval work and/or model-context cost while preserving or improving evidence quality compared with flat lexical retrieval?**

## Current Scope — H1 Experiment

This repository contains the **H1 experimental foundation**: the smallest scientifically meaningful implementation needed to test the hypothesis above.

### What is implemented

- **Source scanning** — walks a real filesystem, detects `.md`, `.txt`, `.pdf` files, tracks identity and versions
- **Content hashing** — SHA-256 file hashing for change detection
- **Resource identity** — stable logical IDs, path normalization, version status tracking (new/modified/unchanged/missing)
- **Parsers** — Markdown heading hierarchy + paragraphs, plain text paragraph detection, PDF page extraction
- **Representation compiler** — compiles structural and lexical representations per resource, produces representation manifests
- **SQLite storage** — normalized schema with FTS5 for lexical search, representation manifests
- **Retrieval strategies:**
  - **Flat FTS baseline** — simple FTS5 over entire indexed corpus
  - **Structure-aware retrieval** — uses precompiled heading/filename signals to narrow candidate documents before passage retrieval
- **Evidence model** — results trace back to resource ID, source path, section, passage, and source version
- **Test suite** — 41 tests covering source immutability, identity, versioning, parsing, persistence, FTS, evidence mapping, incremental indexing, and retrieval comparison

### What is intentionally NOT implemented

- Embeddings, vector databases, ANN search
- Knowledge graphs, GraphRAG, ontology
- LLM-based answer generation (H1 is retrieval-only)
- Adaptive locality, predictive prefetching
- Semantic addressing, transaction engine
- DOCX, XLSX, CSV, image, audio, video processing
- Web dashboard, CLI commands beyond core
- Any infrastructure beyond SQLite

These belong to later research stages (H2+). See `H1_EXPERIMENT.md` for the full execution boundary.

## Project Structure

```
storageos/
├── core/
│   ├── models.py          # Data models
│   ├── hashing.py         # SHA-256 content hashing
│   └── identity.py        # Resource identity, version detection
├── ingest/
│   └── scanner.py         # Filesystem walker, incremental indexing
├── parsers/
│   ├── markdown.py        # Heading hierarchy + paragraph extraction
│   ├── text.py            # Paragraph detection for plain text
│   └── pdf.py             # PDF page extraction
├── representation/
│   ├── compiler.py        # Representation compilation
│   └── manifest.py        # Manifest creation
├── storage/
│   └── database.py        # SQLite schema, CRUD, FTS5
├── retrieval/
│   ├── base.py            # Retriever protocol
│   ├── flat_fts.py        # Baseline: flat FTS5
│   └── structure_aware.py # Experimental: structure-narrowed retrieval
└── tests/
    ├── test_core.py        # Identity, hashing, DB, immutability
    ├── test_parsers.py     # Markdown, text, PDF parsing
    ├── test_scanner.py     # Scanning, incremental updates, compilation
    └── test_retrieval.py   # Both strategies, evidence mapping
```

## Requirements

- Python 3.12+
- SQLite with FTS5 support (included in Python's标准库)
- No external dependencies required for core functionality
- Optional: PyMuPDF (`pip install pymupdf`) for better PDF text extraction (falls back to raw extraction without it)

## Installation

```bash
git clone <repository-url>
cd storageos
pip install -e .
```

Or run directly without installation:

```bash
cd storageos
python -m pytest tests/
```

## Running Tests

```bash
cd storageos
python -m pytest tests/ -v
```

All 41 tests should pass. Tests cover:
- Source immutability (indexing never modifies files)
- Content hashing
- Resource identity and version detection
- Markdown/text/PDF parsing
- SQLite schema and persistence
- FTS5 search
- Source scanner and incremental updates
- Representation compilation
- Both retrieval strategies

## How the H1 Benchmark Works

The H1 experiment compares two retrieval strategies on the same corpus and questions:

1. **Flat FTS** — queries the entire FTS5 index and returns ranked passages
2. **Structure-aware** — uses precompiled heading/filename signals to narrow to candidate documents, then searches within those candidates

For each query, both strategies record:
- Files considered
- Passages inspected
- Bytes read
- Structural nodes visited
- Retrieval latency
- Evidence returned

The experiment measures whether structure-aware retrieval reduces work while preserving evidence quality.

### To run the benchmark on your own corpus

```python
from storageos.storage.database import Database
from storageos.ingest.scanner import scan_directory
from storageos.representation.compiler import compile_all
from storageos.retrieval.flat_fts import FlatFTSRetriever
from storageos.retrieval.structure_aware import StructureAwareRetriever
from pathlib import Path

db = Database(Path("my_index.db"))
db.init_schema()

space_id = db.create_space("my-corpus", "/path/to/my/documents", time.time())
scan_directory(Path("/path/to/my/documents"), db, space_id)
compile_all(db)

flat = FlatFTSRetriever(db)
structured = StructureAwareRetriever(db)

query = "Where did I discuss the architecture?"
flat_result = flat.search(query)
struct_result = structured.search(query)

print(f"Flat FTS: {len(flat_result.evidence)} evidence items, {flat_result.bytes_read} bytes")
print(f"Structure-aware: {len(struct_result.evidence)} evidence items, {struct_result.bytes_read} bytes")
```

## Specification Documents

- **`PRD.md`** — Full StorageOS vision, long-term architecture, and research agenda
- **`H1_EXPERIMENT.md`** — Execution boundary for the first experiment (this implementation)

## License

Research project — see repository for license details.
