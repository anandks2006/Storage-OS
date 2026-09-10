"""Markdown parser — extract heading hierarchy, sections, paragraphs."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from core.models import StructuralNode


def _nid() -> str:
    return f"node-{uuid.uuid4().hex[:12]}"


def parse_markdown(content: str, resource_id: str, version_id: str) -> tuple[list[StructuralNode], list[tuple[str, str, int, int]]]:
    """Parse markdown into structural nodes and (passage_text, passage_id, start, end) tuples."""
    nodes: list[StructuralNode] = []
    passages: list[tuple[str, str, int, int]] = []

    heading_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = list(heading_re.finditer(content))

    if not headings:
        text = content.strip()
        if text:
            nid = _pid()
            pid = f"pass-{uuid.uuid4().hex[:12]}"
            passages.append((text, pid, 0, len(content)))
        return nodes, passages

    # Content before first heading
    pre_text = content[:headings[0].start()].strip()
    if pre_text:
        pid = f"pass-{uuid.uuid4().hex[:12]}"
        passages.append((pre_text, pid, 0, headings[0].start()))

    # Process each heading
    for i, m in enumerate(headings):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)

        nid = _nid()
        node = StructuralNode(
            node_id=nid,
            resource_id=resource_id,
            version_id=version_id,
            node_type="heading",
            level=level,
            title=title,
            start_offset=start,
            end_offset=end,
            parent_id=None,
        )
        nodes.append(node)

        # Extract paragraphs within this section
        section_text = content[start:end]
        para_splits = re.split(r"\n\s*\n", section_text)
        offset = start
        for ps in para_splits:
            ps_stripped = ps.strip()
            if ps_stripped:
                para_start = content.find(ps_stripped, offset)
                if para_start == -1:
                    para_start = offset
                para_end = para_start + len(ps_stripped)
                pid = f"pass-{uuid.uuid4().hex[:12]}"
                passages.append((ps_stripped, pid, para_start, para_end))
            offset += len(ps) + 2  # account for \n\n split

    return nodes, passages


def _pid() -> str:
    return f"pass-{uuid.uuid4().hex[:12]}"
