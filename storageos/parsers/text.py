"""Plain text parser — preserve paragraphs, line numbers, offsets."""
from __future__ import annotations

import uuid
from typing import Optional

from core.models import StructuralNode


def parse_text(content: str, resource_id: str, version_id: str) -> tuple[list[StructuralNode], list[tuple[str, str, int, int]]]:
    """Parse plain text into structural nodes and passages."""
    nodes: list[StructuralNode] = []
    passages: list[tuple[str, str, int, int]] = []

    # Create a single document-level node
    nid = f"node-{uuid.uuid4().hex[:12]}"
    node = StructuralNode(
        node_id=nid,
        resource_id=resource_id,
        version_id=version_id,
        node_type="document",
        level=0,
        title="",
        start_offset=0,
        end_offset=len(content),
    )
    nodes.append(node)

    # Split into paragraphs
    import re
    para_splits = re.split(r"\n\s*\n", content)
    offset = 0
    for ps in para_splits:
        ps_stripped = ps.strip()
        if ps_stripped:
            pid = f"pass-{uuid.uuid4().hex[:12]}"
            para_start = content.find(ps_stripped, offset)
            if para_start == -1:
                para_start = offset
            para_end = para_start + len(ps_stripped)
            passages.append((ps_stripped, pid, para_start, para_end))
        offset += len(ps) + 2

    return nodes, passages
