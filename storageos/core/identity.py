"""Resource identity generation and stable ID management."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from .hashing import hash_file
from .models import ResourceIdentity, SourceType, VersionStatus


EXTENSION_MAP = {
    ".md": SourceType.MARKDOWN,
    ".txt": SourceType.TEXT,
    ".pdf": SourceType.PDF,
}


def source_type_from_extension(ext: str) -> SourceType:
    return EXTENSION_MAP.get(ext.lower(), SourceType.UNKNOWN)


def normalize_path(path: Path) -> str:
    return str(path.resolve())


def generate_resource_id() -> str:
    return f"resource-{uuid.uuid4().hex[:12]}"


def build_resource_identity(path: Path, *, include_hash: bool = True) -> ResourceIdentity:
    stat = path.stat()
    ext = path.suffix.lower()
    now = stat.st_mtime
    content_hash = hash_file(path) if include_hash else None
    return ResourceIdentity(
        resource_id=generate_resource_id(),
        absolute_path=normalize_path(path),
        filename=path.name,
        extension=ext,
        size=stat.st_size,
        mtime=stat.st_mtime,
        content_hash=content_hash,
        source_type=source_type_from_extension(ext),
        first_seen=now,
        last_seen=now,
    )


def detect_version_status(
    existing_hash: Optional[str],
    existing_mtime: float,
    current_mtime: float,
    current_size: Optional[int] = None,
    existing_size: Optional[int] = None,
) -> VersionStatus:
    if existing_hash is None:
        return VersionStatus.NEW
    if current_size is not None and existing_size is not None:
        if current_size != existing_size:
            return VersionStatus.MODIFIED
    if current_mtime != existing_mtime:
        return VersionStatus.MODIFIED
    return VersionStatus.UNCHANGED
