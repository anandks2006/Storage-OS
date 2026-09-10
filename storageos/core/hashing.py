"""Content hashing utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path, algorithm: str = "sha256", chunk_size: int = 65536) -> str:
    """Hash file contents. Returns hex digest."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return f"{algorithm}:{h.hexdigest()}"


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    h.update(data)
    return f"{algorithm}:{h.hexdigest()}"
