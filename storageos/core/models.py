"""Core data models for StorageOS H1."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class SourceType(enum.Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    UNKNOWN = "unknown"


class VersionStatus(enum.Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    NEW = "new"
    MISSING = "missing"


@dataclass
class ResourceIdentity:
    resource_id: str
    absolute_path: str
    filename: str
    extension: str
    size: int
    mtime: float
    content_hash: Optional[str]
    source_type: SourceType
    first_seen: float
    last_seen: float


@dataclass
class ResourceVersion:
    version_id: str
    resource_id: str
    content_hash: str
    status: VersionStatus
    timestamp: float
    size: int
    mtime: float


@dataclass
class StructuralNode:
    node_id: str
    resource_id: str
    version_id: str
    node_type: str  # heading, paragraph, page, section
    level: int
    title: str
    start_offset: int
    end_offset: int
    parent_id: Optional[str] = None


@dataclass
class Passage:
    passage_id: str
    resource_id: str
    version_id: str
    node_id: Optional[str]
    text: str
    start_offset: int
    end_offset: int


@dataclass
class RepresentationManifest:
    manifest_id: str
    resource_id: str
    version_id: str
    identity: bool = True
    structure: bool = True
    lexical: bool = True
    semantic: bool = False
    vector: bool = False
    graph: bool = False
    representation_version: str = "0.1"


@dataclass
class RetrievalResult:
    query: str
    strategy: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    files_considered: int = 0
    passages_considered: int = 0
    structural_nodes_visited: int = 0
    bytes_read: int = 0
    retrieval_latency_ms: float = 0.0


@dataclass
class EvidenceItem:
    resource_id: str
    source_path: str
    passage_id: str
    text: str
    score: float
    node_id: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    source_version: Optional[str] = None
