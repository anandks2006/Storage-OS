"""Download Dolma v1_6-sample shards until ~1.5GB target."""
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\raw")
MANIFEST_PATH = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\MANIFEST.json")
SHARD_LIST_URL = "https://huggingface.co/datasets/allenai/dolma/raw/main/urls/v1_6-sample.txt"
BASE_URL = "https://olmo-data.org/dolma-v1_6-8B-sample/"

TARGET_BYTES = int(1.5 * 1024**3)  # 1.5 GB
HARD_LIMIT = int(2.0 * 1024**3)    # 2.0 GB
MAX_SHARDS = 10

def get_shard_list():
    """Fetch official shard list in listed order."""
    print("Fetching shard list...")
    resp = urllib.request.urlopen(SHARD_LIST_URL, timeout=30)
    text = resp.read().decode("utf-8")
    urls = [line.strip() for line in text.strip().split("\n") if line.strip()]
    print(f"  Found {len(urls)} shards")
    return urls

def download_with_retry(url, dest, max_retries=3):
    """Download a file with retry and resume support."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            })
            # Check for partial file
            existing_size = 0
            if dest.exists():
                existing_size = dest.stat().st_size
                if existing_size > 0:
                    req.add_header("Range", f"bytes={existing_size}-")

            resp = urllib.request.urlopen(req, timeout=120)
            mode = "ab" if existing_size > 0 and resp.status == 206 else "wb"
            total = existing_size if mode == "ab" else 0

            with open(dest, mode) as f:
                while True:
                    chunk = resp.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)

            return dest.stat().st_size
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None

def verify_shard(path):
    """Verify shard is non-zero and readable."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        import gzip
        with gzip.open(path, "rb") as f:
            f.read(1024)  # Try reading first 1KB
        return True
    except Exception:
        return False

def main():
    urls = get_shard_list()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset": "allenai/dolma",
        "version": "v1_6-sample",
        "shard_list_url": SHARD_LIST_URL,
        "download_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "selection_rule": "Sequential from official shard list order, stop before exceeding 1.5GB target (2.0GB hard limit)",
        "target_bytes": TARGET_BYTES,
        "hard_limit_bytes": HARD_LIMIT,
        "shards": [],
        "total_compressed_bytes": 0,
        "total_shards": 0,
    }

    cumulative = 0
    for i, url in enumerate(urls):
        if len(manifest["shards"]) >= MAX_SHARDS:
            print(f"\nReached {MAX_SHARDS} shard limit. Stopping.")
            break

        fname = url.split("/")[-1]
        dest = RAW_DIR / fname

        # Check if already downloaded and verified
        if dest.exists() and verify_shard(dest):
            size = dest.stat().st_size
            print(f"  [{i+1:3d}/{len(urls)}] {fname}: {size/(1024**2):.1f}MB (cached)")
            cumulative += size
            manifest["shards"].append({
                "url": url,
                "local_filename": fname,
                "compressed_bytes": size,
                "verified": True,
                "status": "cached",
            })
            manifest["total_compressed_bytes"] = cumulative
            manifest["total_shards"] = len(manifest["shards"])
            continue

        # Check if adding this shard would exceed target
        # Do a HEAD request to get size
        try:
            req = urllib.request.Request(url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp = urllib.request.urlopen(req, timeout=30)
            shard_size = int(resp.headers.get("Content-Length", 0))
        except Exception:
            # Can't get size, try downloading
            shard_size = 0

        if cumulative + shard_size > HARD_LIMIT:
            print(f"  [{i+1:3d}/{len(urls)}] {fname}: SKIP (would exceed hard limit)")
            break

        if cumulative + shard_size > TARGET_BYTES and cumulative > 0:
            print(f"  [{i+1:3d}/{len(urls)}] {fname}: SKIP (would exceed target)")
            break

        print(f"  [{i+1:3d}/{len(urls)}] {fname}: downloading ({shard_size/(1024**2):.1f}MB)...", end=" ", flush=True)
        actual_size = download_with_retry(url, dest)

        if actual_size is None or actual_size == 0:
            print("FAILED")
            if dest.exists():
                dest.unlink()
            continue

        if not verify_shard(dest):
            print("CORRUPT")
            dest.unlink()
            continue

        print(f"OK ({actual_size/(1024**2):.1f}MB)")
        cumulative += actual_size
        manifest["shards"].append({
            "url": url,
            "local_filename": fname,
            "compressed_bytes": actual_size,
            "verified": True,
            "status": "downloaded",
        })
        manifest["total_compressed_bytes"] = cumulative
        manifest["total_shards"] = len(manifest["shards"])

        # Save manifest incrementally
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2)

    # Final manifest
    manifest["total_compressed_gb"] = round(cumulative / (1024**3), 3)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {len(manifest['shards'])} shards, {cumulative/(1024**3):.3f} GB total")
    print(f"Manifest: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
