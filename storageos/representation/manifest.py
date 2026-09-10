"""Representation manifest model."""
from __future__ import annotations

from core.models import RepresentationManifest


def create_manifest(
    resource_id: str,
    version_id: str,
    *,
    identity: bool = True,
    structure: bool = True,
    lexical: bool = True,
    semantic: bool = False,
    vector: bool = False,
    graph: bool = False,
) -> RepresentationManifest:
    import uuid
    return RepresentationManifest(
        manifest_id=f"manifest-{uuid.uuid4().hex[:12]}",
        resource_id=resource_id,
        version_id=version_id,
        identity=identity,
        structure=structure,
        lexical=lexical,
        semantic=semantic,
        vector=vector,
        graph=graph,
    )
