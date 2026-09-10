"""Tests for source immutability, identity, versioning, and database."""
import time
from pathlib import Path

from core.hashing import hash_file, hash_bytes
from core.identity import (
    build_resource_identity,
    detect_version_status,
    normalize_path,
    source_type_from_extension,
)
from core.models import SourceType, VersionStatus
from storage.database import Database


class TestSourceImmutability:
    """Indexing must not modify source files."""

    def test_indexing_does_not_modify_md(self, sample_md, tmp_db):
        original_hash = hash_file(sample_md)
        from ingest.scanner import scan_directory
        from representation.compiler import compile_resource

        space_id = tmp_db.create_space("test", str(sample_md.parent), time.time())
        scan_directory(sample_md.parent, tmp_db, space_id)
        compile_resource(sample_md, tmp_db, space_id)

        current_hash = hash_file(sample_md)
        assert original_hash == current_hash, "Source file was modified by indexing!"

    def test_indexing_does_not_modify_txt(self, sample_txt, tmp_db):
        original_hash = hash_file(sample_txt)
        from ingest.scanner import scan_directory
        from representation.compiler import compile_resource

        space_id = tmp_db.create_space("test", str(sample_txt.parent), time.time())
        scan_directory(sample_txt.parent, tmp_db, space_id)
        compile_resource(sample_txt, tmp_db, space_id)

        current_hash = hash_file(sample_txt)
        assert original_hash == current_hash, "Source file was modified by indexing!"

    def test_indexing_does_not_modify_pdf(self, sample_pdf, tmp_db):
        original_hash = hash_file(sample_pdf)
        from ingest.scanner import scan_directory
        from representation.compiler import compile_resource

        space_id = tmp_db.create_space("test", str(sample_pdf.parent), time.time())
        scan_directory(sample_pdf.parent, tmp_db, space_id)
        compile_resource(sample_pdf, tmp_db, space_id)

        current_hash = hash_file(sample_pdf)
        assert original_hash == current_hash, "Source file was modified by indexing!"


class TestHashing:
    def test_hash_file(self, sample_md):
        h = hash_file(sample_md)
        assert h.startswith("sha256:")
        assert len(h) > 10

    def test_hash_bytes(self):
        h = hash_bytes(b"hello world")
        assert h.startswith("sha256:")
        assert len(h) > 10

    def test_same_content_same_hash(self, sample_md):
        h1 = hash_file(sample_md)
        h2 = hash_file(sample_md)
        assert h1 == h2


class TestIdentity:
    def test_source_type_from_extension(self):
        assert source_type_from_extension(".md") == SourceType.MARKDOWN
        assert source_type_from_extension(".txt") == SourceType.TEXT
        assert source_type_from_extension(".pdf") == SourceType.PDF
        assert source_type_from_extension(".xyz") == SourceType.UNKNOWN

    def test_build_resource_identity(self, sample_md):
        res = build_resource_identity(sample_md)
        assert res.resource_id.startswith("resource-")
        assert res.filename == "sample.md"
        assert res.extension == ".md"
        assert res.source_type == SourceType.MARKDOWN
        assert res.size > 0
        assert res.content_hash is not None

    def test_normalize_path(self, sample_md):
        n = normalize_path(sample_md)
        assert n == str(sample_md.resolve())

    def test_detect_version_status(self):
        assert detect_version_status(None, 0.0, 1.0) == VersionStatus.NEW
        assert detect_version_status("hash", 1.0, 1.0, 100, 100) == VersionStatus.UNCHANGED
        assert detect_version_status("hash", 1.0, 2.0, 100, 100) == VersionStatus.MODIFIED
        assert detect_version_status("hash", 1.0, 1.0, 100, 200) == VersionStatus.MODIFIED


class TestDatabase:
    def test_init_schema(self, tmp_db):
        # Schema should be created without errors
        conn = tmp_db.connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t["name"] for t in tables}
        assert "resources" in table_names
        assert "resource_versions" in table_names
        assert "structural_nodes" in table_names
        assert "passages" in table_names
        assert "representation_manifests" in table_names

    def test_create_space(self, tmp_db):
        space_id = tmp_db.create_space("test", "/tmp/test", time.time())
        assert space_id.startswith("space-")

    def test_upsert_and_get_resource(self, tmp_db):
        from core.identity import build_resource_identity
        space_id = tmp_db.create_space("test", "/tmp/test", time.time())
        res = build_resource_identity(Path(__file__).resolve())
        tmp_db.upsert_resource(res, space_id)
        fetched = tmp_db.get_resource_by_path(res.absolute_path)
        assert fetched is not None
        assert fetched["resource_id"] == res.resource_id

    def test_insert_and_get_version(self, tmp_db):
        from core.identity import build_resource_identity
        from core.models import ResourceVersion, VersionStatus
        space_id = tmp_db.create_space("test", "/tmp/test", time.time())
        res = build_resource_identity(Path(__file__).resolve())
        tmp_db.upsert_resource(res, space_id)
        ver = ResourceVersion(
            version_id="ver-test-1",
            resource_id=res.resource_id,
            content_hash=res.content_hash or "unknown",
            status=VersionStatus.NEW,
            timestamp=time.time(),
            size=res.size,
            mtime=res.mtime,
        )
        tmp_db.insert_version(ver)
        latest = tmp_db.get_latest_version(res.resource_id)
        assert latest is not None
        assert latest["version_id"] == "ver-test-1"

    def test_fts_search(self, tmp_db):
        from core.models import Passage, ResourceIdentity, ResourceVersion, SourceType, VersionStatus
        space_id = tmp_db.create_space("test", "/tmp/test", time.time())

        # Insert a resource and version first (needed for FK)
        res = ResourceIdentity(
            resource_id="res-1",
            absolute_path="/tmp/test/file.txt",
            filename="file.txt",
            extension=".txt",
            size=100,
            mtime=time.time(),
            content_hash="sha256:abc",
            source_type=SourceType.TEXT,
            first_seen=time.time(),
            last_seen=time.time(),
        )
        tmp_db.upsert_resource(res, space_id)
        ver = ResourceVersion(
            version_id="ver-1",
            resource_id="res-1",
            content_hash="sha256:abc",
            status=VersionStatus.NEW,
            timestamp=time.time(),
            size=100,
            mtime=time.time(),
        )
        tmp_db.insert_version(ver)

        pid = "pass-test-1"
        passage = Passage(
            passage_id=pid,
            resource_id="res-1",
            version_id="ver-1",
            node_id=None,
            text="The quick brown fox jumps over the lazy dog",
            start_offset=0,
            end_offset=43,
        )
        tmp_db.insert_passage(passage)
        results = tmp_db.search_fts("quick fox")
        assert len(results) > 0
        assert any(pid in r["passage_id"] for r in results)

    def test_persistence(self, tmp_path):
        """Database state survives restart."""
        db_path = tmp_path / "persist.db"
        db1 = Database(db_path)
        db1.init_schema()
        space_id = db1.create_space("test", "/tmp", time.time())
        from core.identity import build_resource_identity
        res = build_resource_identity(Path(__file__).resolve())
        db1.upsert_resource(res, space_id)
        db1.close()

        db2 = Database(db_path)
        db2.init_schema()
        fetched = db2.get_resource_by_path(res.absolute_path)
        assert fetched is not None
        assert fetched["resource_id"] == res.resource_id
        db2.close()
