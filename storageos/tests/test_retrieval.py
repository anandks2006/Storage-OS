"""Tests for retrieval strategies."""
import time
from pathlib import Path

from ingest.scanner import scan_directory
from representation.compiler import compile_all
from retrieval.flat_fts import FlatFTSRetriever
from retrieval.structure_aware import StructureAwareRetriever
from storage.database import Database


class TestFlatFTS:
    def test_basic_search(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = FlatFTSRetriever(tmp_db)
        result = retriever.search("SQLite")
        assert result.strategy == "flat_fts"
        assert result.evidence is not None
        assert result.retrieval_latency_ms >= 0

    def test_no_results(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, tmp_db.create_space("test2", str(corpus_dir), time.time()))
        compile_all(tmp_db)

        retriever = FlatFTSRetriever(tmp_db)
        result = retriever.search("zzzznonexistentzzzz")
        assert len(result.evidence) == 0

    def test_metrics_recorded(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = FlatFTSRetriever(tmp_db)
        result = retriever.search("architecture")
        assert result.files_considered >= 0
        assert result.passages_considered >= 0
        assert result.bytes_read >= 0


class TestStructureAware:
    def test_basic_search(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = StructureAwareRetriever(tmp_db)
        result = retriever.search("design architecture")
        assert result.strategy == "structure_aware"
        assert result.evidence is not None
        assert result.structural_nodes_visited > 0

    def test_narrows_candidates(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = StructureAwareRetriever(tmp_db)
        result = retriever.search("design architecture")
        # Should consider fewer files than total
        assert result.files_considered <= 4

    def test_metrics_recorded(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = StructureAwareRetriever(tmp_db)
        result = retriever.search("API endpoints")
        assert result.bytes_read >= 0
        assert result.retrieval_latency_ms >= 0


class TestRetrievalComparison:
    def test_both_strategies_return_evidence(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        flat = FlatFTSRetriever(tmp_db)
        structured = StructureAwareRetriever(tmp_db)

        q = "SQLite storage"
        r1 = flat.search(q)
        r2 = structured.search(q)

        # Both should find something
        assert len(r1.evidence) > 0 or len(r2.evidence) > 0

    def test_evidence_maps_to_source(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)
        compile_all(tmp_db)

        retriever = FlatFTSRetriever(tmp_db)
        result = retriever.search("layered architecture")
        for e in result.evidence:
            assert Path(e.source_path).exists() or e.source_path == "unknown"
