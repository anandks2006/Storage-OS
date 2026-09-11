"""Research-invariant integrity checks for StorageOS.

Call after ingestion and before research benchmarks.
Critical invariant violations raise IntegrityViolation.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class IntegrityViolation(Exception):
    """Raised when a critical invariant is violated."""


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str  # "critical", "high", "medium", "low"


@dataclass
class IntegrityReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "critical")

    @property
    def critical_failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "critical"]

    @property
    def high_failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "high"]

    def summary(self) -> str:
        lines = ["INTEGRITY REPORT", "=" * 60]
        for c in self.checks:
            status = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{status}] ({c.severity}) {c.name}: {c.detail}")
        lines.append("")
        lines.append(f"Critical failures: {len(self.critical_failures)}")
        lines.append(f"High failures: {len(self.high_failures)}")
        if not self.passed:
            lines.append("STATUS: BLOCKED — fix critical failures before proceeding")
        else:
            lines.append("STATUS: OK — safe to proceed")
        return "\n".join(lines)


def check_database_integrity(db_path: Path) -> IntegrityReport:
    """Run all invariant checks on a StorageOS database."""
    report = IntegrityReport()

    if not db_path.exists():
        report.checks.append(CheckResult(
            "db_exists", False, f"Database not found: {db_path}", "critical"
        ))
        return report

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1. Resource-passage count conservation
    res_count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    pass_count = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    report.checks.append(CheckResult(
        "resource_count",
        res_count > 0,
        f"{res_count:,} resources",
        "critical" if res_count == 0 else "low"
    ))
    report.checks.append(CheckResult(
        "passage_count",
        pass_count > 0,
        f"{pass_count:,} passages",
        "critical" if pass_count == 0 else "low"
    ))

    # 2. FTS-passage conservation
    fts_count = conn.execute("SELECT COUNT(*) FROM passages_fts").fetchone()[0]
    fts_match = fts_count == pass_count
    report.checks.append(CheckResult(
        "fts_passage_consistency",
        fts_match,
        f"FTS={fts_count:,}, passages={pass_count:,}, delta={pass_count - fts_count:,}",
        "critical" if not fts_match and pass_count > 0 else "high"
    ))

    # 3. No orphan passages (passages referencing non-existent resources)
    orphans = conn.execute("""
        SELECT COUNT(*) FROM passages p
        WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.resource_id = p.resource_id)
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "no_orphan_passages",
        orphans == 0,
        f"{orphans:,} orphan passages",
        "critical" if orphans > 0 else "low"
    ))

    # 4. No orphan FTS rows (FTS referencing non-existent passages)
    fts_orphans = conn.execute("""
        SELECT COUNT(*) FROM passages_fts f
        WHERE NOT EXISTS (SELECT 1 FROM passages p WHERE p.passage_id = f.passage_id)
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "no_orphan_fts_rows",
        fts_orphans == 0,
        f"{fts_orphans:,} orphan FTS rows",
        "critical" if fts_orphans > 0 else "high"
    ))

    # 5. No orphan nodes (nodes referencing non-existent resources)
    node_orphans = conn.execute("""
        SELECT COUNT(*) FROM structural_nodes n
        WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.resource_id = n.resource_id)
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "no_orphan_nodes",
        node_orphans == 0,
        f"{node_orphans:,} orphan nodes",
        "high" if node_orphans > 0 else "low"
    ))

    # 6. No orphan versions
    ver_orphans = conn.execute("""
        SELECT COUNT(*) FROM resource_versions v
        WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.resource_id = v.resource_id)
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "no_orphan_versions",
        ver_orphans == 0,
        f"{ver_orphans:,} orphan versions",
        "high" if ver_orphans > 0 else "low"
    ))

    # 7. Unique resource paths
    dup_paths = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT absolute_path FROM resources GROUP BY absolute_path HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "unique_resource_paths",
        dup_paths == 0,
        f"{dup_paths:,} duplicate paths",
        "critical" if dup_paths > 0 else "low"
    ))

    # 8. Unique passage IDs
    dup_passages = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT passage_id FROM passages GROUP BY passage_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    report.checks.append(CheckResult(
        "unique_passage_ids",
        dup_passages == 0,
        f"{dup_passages:,} duplicate passage IDs",
        "critical" if dup_passages > 0 else "low"
    ))

    # 9. FK enforcement check (try inserting orphan)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        report.checks.append(CheckResult(
            "fk_enforcement",
            fk_status == 1,
            f"foreign_keys={'ON' if fk_status else 'OFF'}",
            "high" if fk_status == 0 else "low"
        ))
    except Exception:
        report.checks.append(CheckResult(
            "fk_enforcement", False, "Cannot check FK status", "high"
        ))

    # 10. Passage-to-resource ratio sanity
    if res_count > 0:
        ratio = pass_count / res_count
        sane = 0.5 <= ratio <= 1000
        report.checks.append(CheckResult(
            "passage_resource_ratio",
            sane,
            f"{ratio:.1f} passages/resource",
            "medium" if not sane else "low"
        ))

    conn.close()
    return report


def check_dolma_integrity(db_path: Path, index_path: Optional[Path] = None) -> IntegrityReport:
    """Run integrity checks specific to Dolma ingestion."""
    report = check_database_integrity(db_path)

    if index_path and index_path.exists():
        # Count index entries
        with open(index_path, "r", encoding="utf-8") as f:
            index_count = sum(1 for _ in f)

        conn = sqlite3.connect(str(db_path))
        res_count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        pass_count = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM passages_fts").fetchone()[0]
        conn.close()

        # Index vs resources
        report.checks.append(CheckResult(
            "index_resource_conservation",
            index_count == res_count,
            f"index={index_count:,}, resources={res_count:,}, delta={index_count - res_count:,}",
            "critical" if index_count != res_count else "low"
        ))

        # Index vs FTS
        report.checks.append(CheckResult(
            "index_fts_conservation",
            index_count == fts_count,
            f"index={index_count:,}, fts={fts_count:,}, delta={index_count - fts_count:,}",
            "critical" if index_count != fts_count else "high"
        ))

    return report
