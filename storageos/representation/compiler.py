"""Representation compiler — determines what to materialize for each resource."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from core.hashing import hash_file
from core.models import (
    Passage,
    RepresentationManifest,
    ResourceIdentity,
    ResourceVersion,
    SourceType,
    StructuralNode,
)
from parsers.markdown import parse_markdown
from parsers.text import parse_text
from parsers.pdf import parse_pdf
from storage.database import Database


def compile_resource(path: Path, db: Database, space_id: str) -> Optional[str]:
    """Compile representations for a single resource. Returns resource_id or None on failure."""
    from core.identity import build_resource_identity, normalize_path
    from core.models import VersionStatus

    abs_path = normalize_path(path)
    existing = db.get_resource_by_path(abs_path)

    if not existing:
        return None

    resource_id = existing["resource_id"]
    latest = db.get_latest_version(resource_id)
    if not latest:
        return None

    version_id = latest["version_id"]
    content_hash = latest["content_hash"]

    # Check if representations already exist for this version
    existing_nodes = db.get_nodes_for_resource(resource_id)
    if existing_nodes and existing_nodes[0]["version_id"] == version_id:
        return resource_id  # Already compiled

    source_type = SourceType(existing["source_type"])
    content = path.read_bytes()

    try:
        if source_type == SourceType.MARKDOWN:
            text = content.decode("utf-8", errors="replace")
            nodes, raw_passages = parse_markdown(text, resource_id, version_id)
        elif source_type == SourceType.TEXT:
            text = content.decode("utf-8", errors="replace")
            nodes, raw_passages = parse_text(text, resource_id, version_id)
        elif source_type == SourceType.PDF:
            nodes, raw_passages = parse_pdf(path, resource_id, version_id)
        else:
            return None
    except Exception as e:
        print(f"PARSE FAILED: {path}: {e}")
        return None

    # Insert structural nodes
    for node in nodes:
        db.insert_structural_node(node)

    # Insert passages
    for text_content, pid, start, end in raw_passages:
        passage = Passage(
            passage_id=pid,
            resource_id=resource_id,
            version_id=version_id,
            node_id=nodes[0].node_id if nodes else None,
            text=text_content,
            start_offset=start,
            end_offset=end,
        )
        db.insert_passage(passage)

    # Insert manifest
    manifest = RepresentationManifest(
        manifest_id=f"manifest-{uuid.uuid4().hex[:12]}",
        resource_id=resource_id,
        version_id=version_id,
        identity=True,
        structure=len(nodes) > 0,
        lexical=True,
    )
    db.insert_manifest(manifest)

    return resource_id


def compile_all(db: Database) -> dict:
    """Compile representations for all indexed resources."""
    stats = {"compiled": 0, "skipped": 0, "failed": 0}
    resources = db.get_all_resources()

    for res in resources:
        path = Path(res["absolute_path"])
        if not path.exists():
            stats["failed"] += 1
            continue
        result = compile_resource(path, db, space_id="default")
        if result:
            stats["compiled"] += 1
        else:
            stats["failed"] += 1

    return stats
