"""PDF parser — extract page boundaries, text, basic headings."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from core.models import StructuralNode


def parse_pdf(path: Path, resource_id: str, version_id: str) -> tuple[list[StructuralNode], list[tuple[str, str, int, int]]]:
    """Parse PDF into structural nodes (pages) and passages.

    Falls back to raw byte scanning if PyMuPDF is unavailable.
    """
    nodes: list[StructuralNode] = []
    passages: list[tuple[str, str, int, int]] = []

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if not text.strip():
                continue
            nid = f"node-{uuid.uuid4().hex[:12]}"
            pid = f"pass-{uuid.uuid4().hex[:12]}"
            node = StructuralNode(
                node_id=nid,
                resource_id=resource_id,
                version_id=version_id,
                node_type="page",
                level=0,
                title=f"Page {page_num + 1}",
                start_offset=page_num,
                end_offset=page_num + 1,
            )
            nodes.append(node)
            passages.append((text.strip(), pid, page_num, page_num + 1))
        doc.close()
    except ImportError:
        # Minimal fallback: treat entire file as one page
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        nid = f"node-{uuid.uuid4().hex[:12]}"
        pid = f"pass-{uuid.uuid4().hex[:12]}"
        node = StructuralNode(
            node_id=nid,
            resource_id=resource_id,
            version_id=version_id,
            node_type="page",
            level=0,
            title="Page 1",
            start_offset=0,
            end_offset=1,
        )
        nodes.append(node)
        passages.append((text.strip(), pid, 0, 1))

    return nodes, passages
