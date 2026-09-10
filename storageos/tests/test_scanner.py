"""Tests for source scanner and incremental updates."""
import time
from pathlib import Path

from core.hashing import hash_file
from core.identity import normalize_path
from ingest.scanner import scan_directory
from representation.compiler import compile_resource
from storage.database import Database


class TestScanner:
    def test_scan_finds_files(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        stats = scan_directory(corpus_dir, tmp_db, space_id)
        assert stats["total"] == 4  # readme.md, notes.txt, design.md, api.txt
        assert stats["new"] == 4
        assert stats["failed"] == 0

    def test_scan_skips_non_supported(self, tmp_path, tmp_db):
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "data.csv").write_text("a,b,c\n")
        (tmp_path / "good.md").write_text("# Hello\n")
        space_id = tmp_db.create_space("test", str(tmp_path), time.time())
        stats = scan_directory(tmp_path, tmp_db, space_id)
        assert stats["total"] == 1  # only .md

    def test_incremental_scan(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)

        # Modify one file
        readme = corpus_dir / "readme.md"
        readme.write_text("# Updated README\n\nChanged content.\n", encoding="utf-8")

        stats = scan_directory(corpus_dir, tmp_db, space_id)
        assert stats["modified"] >= 1
        assert stats["unchanged"] >= 2

    def test_new_file_detected(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)

        (corpus_dir / "newfile.md").write_text("# New\n\nBrand new file.\n", encoding="utf-8")
        stats = scan_directory(corpus_dir, tmp_db, space_id)
        assert stats["new"] >= 1


class TestCompiler:
    def test_compile_markdown(self, sample_md, tmp_db):
        space_id = tmp_db.create_space("test", str(sample_md.parent), time.time())
        scan_directory(sample_md.parent, tmp_db, space_id)
        resource_id = compile_resource(sample_md, tmp_db, space_id)
        assert resource_id is not None

        nodes = tmp_db.get_nodes_for_resource(resource_id)
        assert len(nodes) >= 2  # at least 2 headings

        passages = tmp_db.get_passages_for_resource(resource_id)
        assert len(passages) >= 2

    def test_compile_text(self, sample_txt, tmp_db):
        space_id = tmp_db.create_space("test", str(sample_txt.parent), time.time())
        scan_directory(sample_txt.parent, tmp_db, space_id)
        resource_id = compile_resource(sample_txt, tmp_db, space_id)
        assert resource_id is not None

        passages = tmp_db.get_passages_for_resource(resource_id)
        assert len(passages) >= 2

    def test_compile_all(self, corpus_dir, tmp_db):
        space_id = tmp_db.create_space("test", str(corpus_dir), time.time())
        scan_directory(corpus_dir, tmp_db, space_id)

        from representation.compiler import compile_all
        stats = compile_all(tmp_db)
        assert stats["compiled"] == 4
        assert stats["failed"] == 0

    def test_manifest_created(self, sample_md, tmp_db):
        space_id = tmp_db.create_space("test", str(sample_md.parent), time.time())
        scan_directory(sample_md.parent, tmp_db, space_id)
        compile_resource(sample_md, tmp_db, space_id)

        conn = tmp_db.connect()
        manifests = conn.execute("SELECT * FROM representation_manifests").fetchall()
        assert len(manifests) == 1
        assert manifests[0]["identity_rep"] == 1
        assert manifests[0]["structure_rep"] == 1
        assert manifests[0]["lexical_rep"] == 1

    def test_idempotent_compile(self, sample_md, tmp_db):
        space_id = tmp_db.create_space("test", str(sample_md.parent), time.time())
        scan_directory(sample_md.parent, tmp_db, space_id)
        compile_resource(sample_md, tmp_db, space_id)
        compile_resource(sample_md, tmp_db, space_id)  # second call

        conn = tmp_db.connect()
        nodes = conn.execute("SELECT COUNT(*) as cnt FROM structural_nodes").fetchone()["cnt"]
        passages = conn.execute("SELECT COUNT(*) as cnt FROM passages").fetchone()["cnt"]
        # Should not double-insert
        assert nodes <= 5  # reasonable upper bound for our test file
