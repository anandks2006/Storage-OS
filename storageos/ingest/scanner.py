"""Source scanner — walks filesystem, detects resources, manages identity/version."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from core.hashing import hash_file
from core.identity import (
    build_resource_identity,
    detect_version_status,
    normalize_path,
    source_type_from_extension,
)
from core.models import (
    ResourceIdentity,
    ResourceVersion,
    SourceType,
    VersionStatus,
)
from storage.database import Database


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


def scan_directory(root: Path, db: Database, space_id: str) -> dict:
    """Scan directory and index all supported files.

    Returns summary dict with counts of new/modified/unchanged/failed.
    """
    stats = {"new": 0, "modified": 0, "unchanged": 0, "failed": 0, "total": 0}
    now = time.time()

    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            fpath = Path(dirpath) / fname
            ext = fpath.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            stats["total"] += 1
            try:
                status = _index_file(fpath, db, space_id, now)
                stats[status] = stats.get(status, 0) + 1
            except Exception as e:
                stats["failed"] += 1
                print(f"FAILED: {fpath}: {e}")

    return stats


def _index_file(path: Path, db: Database, space_id: str, now: float) -> str:
    """Index a file and return its status: 'new', 'modified', or 'unchanged'."""
    abs_path = normalize_path(path)
    existing = db.get_resource_by_path(abs_path)

    if existing:
        new_mtime = path.stat().st_mtime
        new_size = path.stat().st_size
        status = detect_version_status(
            existing_hash=existing["content_hash"],
            existing_mtime=existing["mtime"],
            current_mtime=new_mtime,
            current_size=new_size,
            existing_size=existing["size"],
        )
        if status == VersionStatus.UNCHANGED:
            return "unchanged"

        content_hash = hash_file(path)
        res_id = existing["resource_id"]
        res = ResourceIdentity(
            resource_id=res_id,
            absolute_path=abs_path,
            filename=path.name,
            extension=path.suffix.lower(),
            size=new_size,
            mtime=new_mtime,
            content_hash=content_hash,
            source_type=source_type_from_extension(path.suffix.lower()),
            first_seen=existing["first_seen"],
            last_seen=now,
        )
        db.upsert_resource(res, space_id)

        ver = ResourceVersion(
            version_id=f"ver-{res_id}-{int(now)}",
            resource_id=res_id,
            content_hash=content_hash,
            status=VersionStatus.MODIFIED,
            timestamp=now,
            size=new_size,
            mtime=new_mtime,
        )
        db.insert_version(ver)
        return "modified"
    else:
        res = build_resource_identity(path, include_hash=True)
        db.upsert_resource(res, space_id)
        ver = ResourceVersion(
            version_id=f"ver-{res.resource_id}-{int(now)}",
            resource_id=res.resource_id,
            content_hash=res.content_hash or "unknown",
            status=VersionStatus.NEW,
            timestamp=now,
            size=res.size,
            mtime=res.mtime,
        )
        db.insert_version(ver)
        return "new"
