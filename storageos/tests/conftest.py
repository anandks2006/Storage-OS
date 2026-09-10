"""Pytest configuration and shared fixtures."""
import sys
import tempfile
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from storage.database import Database


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a fresh temporary database."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    yield db
    db.close()


@pytest.fixture
def sample_md(tmp_path):
    """Create a sample markdown file."""
    content = """# Main Title

This is the introduction paragraph.

## Section A

Content about topic A with important details.

## Section B

Content about topic B with different information.

### Subsection B1

More detailed content in subsection B1.
"""
    path = tmp_path / "sample.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_txt(tmp_path):
    """Create a sample text file."""
    content = """First paragraph with some content here.

Second paragraph about a different topic.

Third paragraph wrapping up the discussion.
"""
    path = tmp_path / "sample.txt"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal PDF file for testing."""
    # Minimal valid PDF
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000360 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
428
%%EOF"""
    path = tmp_path / "sample.pdf"
    path.write_bytes(content)
    return path


@pytest.fixture
def corpus_dir(tmp_path):
    """Create a multi-file corpus for integration tests."""
    root = tmp_path / "corpus"
    root.mkdir()

    (root / "readme.md").write_text("# Project README\n\nThis is the main readme.\n", encoding="utf-8")
    (root / "notes.txt").write_text("Some notes about the project.\n\nMore notes here.\n", encoding="utf-8")
    sub = root / "docs"
    sub.mkdir()
    (sub / "design.md").write_text("# Design Doc\n\n## Architecture\n\nThe system uses a layered architecture.\n\n## Storage\n\nData is stored in SQLite.\n", encoding="utf-8")
    (sub / "api.txt").write_text("API Reference\n\nEndpoints:\n\nGET /search\nPOST /index\n", encoding="utf-8")

    return root
