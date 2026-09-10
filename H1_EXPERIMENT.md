# StorageOS — H1 Experimental Build Specification

## Status

This document is the **execution boundary for the first StorageOS experiment**.

It is subordinate to `PRD.md`.

`PRD.md` defines the full StorageOS vision, long-term architecture, protocol, product capabilities, and research agenda. `H1_EXPERIMENT.md` defines what OpenCode is permitted and required to build **right now**.

The first objective is not to build the full StorageOS product.

The first objective is to obtain a rigorous experimental result for H1:

> **Can a retrieval-aware representation, compiled before retrieval and before expensive semantic indexing, reduce retrieval work and/or model-context cost while preserving or improving evidence quality compared with flat lexical retrieval?**

The experiment must be small enough to run on constrained consumer hardware, but architected so that successful results can later grow into the full StorageOS system without rewriting the core model.

---

# 1. Relationship to the Master PRD

The master PRD defines:

- immutable source data
- universal information model
- representation compilation
- multi-resolution information
- cost-aware retrieval
- adaptive locality
- semantic addressing
- persistent context
- multimodal evidence
- transactional AI operations
- research benchmarking

This experiment implements only the smallest subset necessary to test H1.

Do not interpret the narrower implementation scope as deletion of future requirements.

Future capabilities must remain architecturally possible, but must **not** be implemented now unless required by H1.

---

# 2. H1 Research Question

We need to test whether deliberate representation of document structure before retrieval can outperform flat retrieval in at least one meaningful efficiency dimension.

The experiment asks:

1. Can structure-aware indexing reduce the amount of information that must be searched?
2. Can it reduce the amount of information returned to the model?
3. Can it reduce retrieval latency?
4. Can it reduce computational work?
5. Can it preserve or improve evidence quality?
6. Does the benefit remain on messy real-world file organization?
7. What is the total lifetime cost after repeated queries?

The experiment must measure both **quality** and **cost**.

A system that is cheaper but retrieves worse evidence is not a success.

A system that retrieves better evidence but costs dramatically more is also not automatically a success.

---

# 3. Experimental Scope

## 3.1 Source types

Only:

- Markdown (`.md`)
- plain text (`.txt`)
- PDF (`.pdf`)

No additional source types in H1.

Do not implement:

- DOCX
- PPTX
- XLSX
- CSV-specific processing
- source-code parsing
- images
- audio
- video
- archives
- email
- databases
- cloud adapters

Those belong to later stages.

---

# 4. Corpus

Use a real folder selected by the user.

Preferred size:

- minimum useful corpus: ~100 source files
- normal experimental corpus: ~100–1,000 source files
- larger corpus is optional if hardware permits

The corpus should contain realistic mess where possible:

- inconsistent filenames
- nested directories
- duplicate ideas
- unrelated material
- old documents
- related information spread across files
- long documents
- short documents
- sections with misleading titles
- documents with overlapping terminology

Do not modify source files to prepare the experiment.

The experiment should work on the corpus exactly as found.

---

# 5. Benchmark Question Set

Create approximately 20–50 real questions about the selected corpus.

Questions should include:

## Exact lookup

Examples:

- Where is the document discussing X?
- Which file contains Y?

## Lexical lookup

Examples:

- Find documents containing the phrase “hierarchical retrieval”.

## Structural lookup

Examples:

- In which section is X discussed?
- Which chapter discusses Y?

## Semantic-ish natural-language lookup

Examples:

- Where did I discuss reducing token usage?
- Which document explains incremental indexing?

The benchmark should include both easy and difficult queries.

Do not optimize the benchmark questions after seeing results without recording that change.

---

# 6. Ground Truth

Every benchmark query must have manually established ground truth.

Ground truth should identify:

- relevant source documents
- relevant pages for PDFs
- relevant sections/headings
- relevant paragraphs/passages where practical

Ground truth must be stored separately from retrieval results.

A query must never be considered successful merely because the result “looks plausible”.

---

# 7. Non-Goals for H1

Do not implement:

- embeddings
- vector databases
- ANN search
- ontology
- knowledge graph
- semantic graph traversal
- GraphRAG
- RAPTOR
- LightRAG
- LeanRAG
- ColBERT
- bandit routing
- Dijkstra
- A*
- beam search
- PCST
- set cover
- adaptive locality learning
- predictive prefetching
- semantic addresses
- human-readable what3words-style addressing
- AI filesystem mutation
- transaction engine
- persistent conversation memory
- Context Virtual Memory
- multimodal deep analysis
- web dashboard beyond what is minimally needed for debugging, if any

These are future research/product stages.

---

# 8. Core H1 Architecture

The first implementation should be:

```text
REAL FILESYSTEM
       |
       v
SOURCE OBSERVER
       |
       v
CONTENT IDENTITY / VERSION
       |
       v
REPRESENTATION COMPILER v0.1
       |
       +-------------------+
       |                   |
       v                   v
STRUCTURAL MODEL        LEXICAL MODEL
       |                   |
       +---------+---------+
                 |
                 v
              SQLITE
                 |
        +--------+--------+
        |                 |
        v                 v
   FLAT FTS          STRUCTURE-AWARE
   BASELINE            RETRIEVAL
        |                 |
        +--------+--------+
                 |
                 v
           EVIDENCE SET
                 |
                 v
            BENCHMARK
```

---

# 9. Source Immutability

This is a hard invariant.

Indexing must not:

- modify files
- rename files
- move files
- delete files
- rewrite files
- alter document content
- write metadata into source documents

Before indexing, the system should record sufficient source identity information to later verify that the source has not been changed by StorageOS.

Tests must verify this.

---

# 10. Stable Resource Identity

Every source object needs a stable logical ID.

At minimum, record:

- logical resource ID
- absolute/normalized path
- filename
- extension
- size
- modification time
- content hash where appropriate
- source type
- first-seen timestamp
- last-seen timestamp

The identity model must be future-compatible with movement and version tracking, even though full cross-location identity resolution is not required for H1.

---

# 11. Source Version Detection

The implementation must detect whether a previously indexed source has changed.

For H1:

- metadata checks may be used as a fast preliminary check
- content hashing may be used when required
- unchanged sources must not be reparsed unnecessarily

The system must distinguish:

- unchanged
- modified
- new
- missing

---

# 12. PDF Representation

For PDFs, extract only what H1 requires:

- document identity
- page boundaries
- page text
- headings where reasonably detectable
- paragraph boundaries where reasonably detectable

Do not implement deep semantic PDF understanding.

Do not invoke an LLM just to determine page/heading/paragraph structure if deterministic extraction is sufficient.

---

# 13. Markdown Representation

For Markdown, extract:

- heading hierarchy
- section boundaries
- paragraphs
- source offsets where practical

Example:

```text
Document
├── H1
│   ├── H2
│   │   ├── paragraph
│   │   └── paragraph
│   └── H2
└── H1
```

---

# 14. TXT Representation

Plain text may not have explicit hierarchy.

For TXT:

- preserve paragraphs where detectable
- preserve line numbers
- preserve offsets
- store basic structural boundaries

Do not invent semantic hierarchy where none exists.

---

# 15. Representation Manifest

Every indexed resource must have a representation manifest.

Example:

```json
{
  "resource_id": "resource-123",
  "source_version": "sha256:...",
  "source_type": "pdf",
  "representations": {
    "identity": true,
    "structure": true,
    "lexical": true,
    "semantic": false,
    "vector": false,
    "graph": false
  }
}
```

The manifest exists to demonstrate that representation selection occurs explicitly before retrieval.

---

# 16. Representation Compiler v0.1

The compiler should determine, for each source:

- detected type
- available deterministic structure
- available representations
- which representations are materialized
- which representations remain disabled/lazy
- representation version

For H1, the compiler is deterministic.

Do not introduce machine learning merely to choose between:

- identity
- structure
- lexical

because that would add experimental noise.

---

# 17. SQLite Persistence

Use SQLite as the canonical database.

The database must contain enough information to reconstruct the H1 representation.

Suggested logical tables:

```text
spaces
resources
resource_versions
structural_nodes
passages
representation_manifests
```

FTS5 should be used for lexical search.

Do not require:

- PostgreSQL
- Neo4j
- Redis
- Kafka
- external message queues
- vector DB

---

# 18. Evidence Model

Every retrievable result must be traceable to source evidence.

For H1, evidence should be able to identify:

- resource ID
- source path
- page/section/paragraph when available
- text span or passage ID
- source version

The returned evidence should be directly inspectable.

---

# 19. Retrieval Strategy A — Flat FTS Baseline

The baseline should be intentionally simple.

Process:

```text
query
  |
  v
FTS5 over the entire indexed lexical corpus
  |
  v
ranked passages/documents
```

This baseline establishes the cost of flat lexical retrieval.

It must be deterministic and reproducible.

---

# 20. Retrieval Strategy B — Structure-Aware Retrieval

The experimental strategy should exploit the structural representation.

Initial implementation can use deterministic signals such as:

- query term occurrence at section/heading level
- matching heading text
- matching filenames
- section-level lexical signals
- parent/child document structure
- candidate-region narrowing

Example:

```text
query
  |
  v
candidate documents
  |
  v
candidate sections
  |
  v
candidate passages
  |
  v
final evidence
```

Do not introduce embeddings.

Do not introduce an LLM planner.

The purpose is to isolate the contribution of precompiled structure.

---

# 21. Important Experimental Distinction

Do not compare:

```text Flat FTS
vs
a completely different semantic AI system
```

The H1 comparison should isolate the effect of **representation-aware retrieval**.

The only major difference between the baseline and experiment should be how the pre-indexed information representation is used to narrow/organize retrieval.

---

# 22. Evidence Quality

For every query, evaluate:

## Evidence Recall

Did the method retrieve the known relevant evidence?

## Evidence Precision

How much of what it retrieved was actually relevant?

## Sufficiency

Could a reasonable answer be produced from the returned evidence without returning the entire corpus?

The benchmark should preserve both automatic metrics and a manual sufficiency assessment.

---

# 23. Retrieval Work Metrics

Record as many of the following as can be measured reliably:

- number of source files considered
- number of documents searched
- number of structural nodes visited
- number of passages considered
- number of FTS candidates
- bytes read
- SQLite query time
- CPU time
- end-to-end latency

Do not fabricate a metric if the implementation cannot measure it accurately.

---

# 24. Model/Token Metrics

H1 should be largely LLM-independent.

However, if an LLM is used to turn evidence into answers, record:

- model/provider
- input tokens
- output tokens
- total tokens
- number of calls

The exact same model/configuration must be used for both retrieval strategies when comparing answer generation.

The retrieval experiment must not gain an unfair advantage from using a different model.

---

# 25. Indexing Cost

Record:

- total indexing time
- parsing time
- SQLite insertion time
- index size
- source bytes processed
- number of generated representations

Where possible distinguish:

```text initial indexing cost
```

from:

```text incremental update cost
```

---

# 26. Lifetime Cost

The experiment must not stop at initial indexing.

Evaluate:

```text LifetimeCost(N)
=
InitialIndexCost
+
sum(QueryCost_1 ... QueryCost_N)
```

Test multiple workload sizes where practical:

- 1 query
- 10 queries
- 100 queries
- larger repeated workloads if feasible

The purpose is to determine whether a representation investment pays off over repeated use.

---

# 27. Workload Classes

Benchmark at least two patterns.

## Cold workload

Mostly unrelated questions.

This measures whether the representation itself provides value.

## Repeated workload

Many questions about related portions of the corpus.

H2 is not implemented yet, but this workload creates the baseline needed to later test adaptive locality.

---

# 28. Adversarial Corpus Conditions

Where practical, include difficult corpus conditions:

- misleading filenames
- deeply nested folders
- duplicated concepts
- common keywords appearing in irrelevant documents
- relevant evidence buried in long documents
- relevant concepts spread across multiple documents

The purpose is to prevent the system from appearing successful merely because filenames are clean.

---

# 29. Benchmark Runner

Create a single command that can execute all H1 queries against both strategies.

Example:

```text
storageos benchmark h1
```

It should produce:

```text
results/
├── run-<timestamp>.json
├── run-<timestamp>.csv
└── report-<timestamp>.md
```

The machine-readable output should contain all raw measurements.

---

# 30. Reproducibility

Every benchmark run must record:

- benchmark version
- corpus identifier
- source hashes
- StorageOS version/commit
- retrieval strategy
- configuration
- model configuration if used
- timestamp
- hardware information where practical

Do not overwrite old results.

---

# 31. Benchmark Result Format

Each query result should contain something approximately like:

```json
{
  "query_id": "Q17",
  "strategy": "structure_aware",
  "retrieved_evidence": [],
  "evidence_recall": 0.0,
  "evidence_precision": 0.0,
  "files_considered": 0,
  "passages_considered": 0,
  "bytes_read": 0,
  "retrieval_latency_ms": 0,
  "input_tokens": 0,
  "output_tokens": 0,
  "model_calls": 0
}
```

Actual schema may be improved during implementation.

---

# 32. H1 Success Criteria

Do not define success as a single arbitrary percentage.

H1 is promising if, on a meaningful portion of benchmark queries, the structure-aware strategy demonstrates a measurable reduction in retrieval work and/or context cost while preserving or improving evidence quality.

Report:

```text
wins
ties
regressions
```

by query class.

The result must be honest.

---

# 33. H1 Failure Conditions

H1 should be considered unsupported if:

- efficiency gains are negligible,
- gains occur only on trivial queries,
- gains come with unacceptable evidence loss,
- the additional representation cost dominates lifetime savings,
- or the structure-aware method is consistently worse than flat FTS.

A negative result should be preserved as a legitimate research result.

---

# 34. Do Not Optimize the Experiment After Seeing Results

The first benchmark configuration becomes the baseline.

If changes are made afterward:

- version the benchmark
- document the change
- rerun the prior benchmark
- keep both result sets

Do not quietly tune the system until it wins.

---

# 35. Tests

Required tests:

## Source integrity

Indexing does not modify source files.

## Identity

Repeated scans identify unchanged resources correctly.

## Versioning

Modified resources create a new source version.

## Parsing

PDF/Markdown/TXT structure is extracted correctly.

## Persistence

Database state survives restart.

## FTS

Search returns expected lexical results.

## Evidence

Results map back to source locations.

## Benchmark

The benchmark runner produces reproducible structured results.

---

# 36. Failure Recovery

If one file cannot be parsed:

- log the failure
- continue indexing other files
- mark the resource as partially/unavailable
- allow retry

A malformed file must not invalidate the entire corpus.

---

# 37. Incremental Update Test

Create a benchmark fixture where:

```text
100 documents indexed
```

then modify only:

```text
1 document
```

The second indexing pass should process only the changed resource plus any H1-required dependent representations.

Measure:

- files reparsed
- time
- database updates

---

# 38. Resource Constraints

The experiment must run acceptably on a modest CPU-only laptop.

Do not assume:

- GPU
- >8 GB RAM
- unlimited API calls
- unlimited embeddings
- paid inference

The H1 implementation must work with zero LLM calls.

---

# 39. Dependency Policy

Prefer a small dependency set.

Core:

- Python 3.12+
- SQLite
- SQLite FTS5
- standard library where practical

Add format-specific libraries only when required for Markdown/PDF processing.

Do not introduce infrastructure dependencies.

---

# 40. Repository Layout for H1

Suggested:

```text
storageos/
├── core/
│   ├── models.py
│   ├── identity.py
│   ├── versions.py
│   └── provenance.py
│
├── ingest/
│   ├── scanner.py
│   ├── hashing.py
│   └── pipeline.py
│
├── parsers/
│   ├── markdown.py
│   ├── text.py
│   └── pdf.py
│
├── representation/
│   ├── manifest.py
│   └── compiler.py
│
├── storage/
│   ├── database.py
│   └── repositories.py
│
├── retrieval/
│   ├── base.py
│   ├── flat_fts.py
│   └── structure_aware.py
│
├── benchmark/
│   ├── runner.py
│   ├── metrics.py
│   ├── schemas.py
│   └── reports.py
│
├── cli.py
└── tests/
```

This is a suggested structure, not a rigid requirement.

Use OpenCode's judgment if a simpler structure is objectively better.

---

# 41. CLI for H1

Minimum commands:

```text
storageos init
storageos scan <path>
storageos status
storageos search <query>
storageos benchmark h1
```

Optional diagnostic commands:

```text
storageos inspect <resource-id>
storageos tree <resource-id>
storageos verify-source <path>
```

---

# 42. Programmatic API

The retrieval strategies must share an interface.

Conceptually:

```python
class Retriever(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> RetrievalResult:
        ...
```

This is important because future algorithms must be able to plug into the same benchmark harness.

---

# 43. Future Compatibility Requirements

Even though advanced systems are not implemented, avoid architectural decisions that make them impossible.

The current model should be capable of eventually accommodating:

```text graph
ontology
vectors
late interaction
semantic addresses
locality
context
multimodal evidence
```

without rewriting:

```text resource identity
source versioning
evidence identity
basic representation model
benchmark interface
```

Do not build those future systems prematurely.

---

# 44. Research Logging

Every retrieval execution should optionally expose a diagnostic trace:

```text query
→ candidate region
→ structural filtering
→ lexical retrieval
→ selected evidence
```

This is essential for understanding why the experimental strategy succeeds or fails.

---

# 45. Answer Generation

If an LLM is used for answer generation:

```text same evidence
same model
same prompt policy
same model settings
```

must be used across baseline and experimental retrieval where possible.

The retrieval experiment should compare retrieval, not model selection.

---

# 46. Token Measurement

Token measurement must distinguish:

```text query tokens
retrieved evidence tokens
prompt/instruction tokens
output tokens
```

Where the provider does not expose exact token counts, use a documented tokenizer/estimation method and label it as estimated.

Never present estimated values as exact.

---

# 47. Research Report

The benchmark report should answer:

1. Did structure-aware retrieval reduce retrieval work?
2. Did it reduce model-context tokens?
3. Did it reduce latency?
4. Did it preserve evidence recall?
5. Where did it fail?
6. Which query classes benefited?
7. What was the extra indexing cost?
8. What is the break-even query count?
9. Does the hypothesis justify H2?

---

# 48. Required Break-Even Analysis

Calculate an approximate query count `N*` where:

```text
Cost(structure-aware)
<
Cost(flat)
```

including the extra initial representation cost.

Conceptually:

```text
IndexExtraCost
+
N × StructureAwareQueryCost
<
N × FlatQueryCost
```

Solve for `N` where meaningful.

This is one of the most important H1 outputs.

---

# 49. H1 Decision Gate

At the end of the experiment, generate one of:

```text
H1 SUPPORTED
H1 PARTIALLY SUPPORTED
H1 INCONCLUSIVE
H1 NOT SUPPORTED
```

with evidence.

Do not proceed to H2 merely because the system is technically working.

Proceed only if the evidence provides a credible reason to investigate adaptive locality.

---

# 50. Next Stage Trigger

Only after H1 results are reviewed should the next capability be selected.

If H1 is promising:

```text
H1
→ H2 Adaptive Locality
```

Possible H2 additions:

- route statistics
- frequency
- recency
- semantic locality
- cache promotion
- repeated-query optimization

If H1 is weak:

Do not automatically add complexity.

First determine:

- whether the representation is insufficient
- whether structural routing is too primitive
- whether the workload is inappropriate
- whether another representation should be tested

---

# 51. OpenCode Operating Rules

OpenCode must:

1. Read `PRD.md` and this file completely.
2. Treat this file as the current execution boundary.
3. Preserve the long-term model without implementing future features.
4. Never delete future requirements from `PRD.md`.
5. Never add unnecessary infrastructure.
6. Never use an LLM where a deterministic method can answer the H1 question.
7. Write tests alongside implementation.
8. Run tests frequently.
9. Keep benchmark instrumentation from the beginning.
10. Preserve source immutability.
11. Record assumptions.
12. Never fabricate benchmark results.
13. Never silently change benchmark methodology.
14. Prefer simple code over speculative abstractions.
15. Keep future retrieval strategies behind replaceable interfaces.

---

# 52. Explicit Anti-Scope-Creep Rule

During H1, if OpenCode discovers a potentially useful future idea, do not automatically implement it.

Instead:

```text
document the idea
→ explain why it may matter
→ identify the future stage
→ continue H1
```

Examples:

```text "A graph might improve this query."
→ record as future H2/H3/research work.

"Embeddings could improve recall."
→ record as future baseline.

"Semantic addresses would be useful."
→ record for later.
```

The experiment must remain interpretable.

---

# 53. Explicit Anti-Underbuilding Rule

Do not make the H1 experiment so weak that it cannot actually test the hypothesis.

The implementation must genuinely:

- compile a representation before retrieval
- use structural information during retrieval
- measure retrieval work
- measure evidence quality
- compare against a flat baseline
- account for indexing cost
- support repeated workloads

A toy keyword filter is not sufficient if it does not meaningfully use the precompiled representation.

---

# 54. Definition of Done

H1 is complete only when:

- source immutability is tested
- real Markdown/TXT/PDF data can be indexed
- resource identity works
- versions are detected
- structural representation exists
- representation manifests exist
- SQLite persistence works
- FTS baseline works
- structure-aware retrieval works
- both strategies run through the same benchmark harness
- ground truth exists
- evidence quality is measured
- retrieval cost is measured
- indexing cost is measured
- lifetime cost is analyzed
- results are reproducible
- an H1 conclusion is produced

---

# 55. The One Loop

The first experiment should ultimately reduce to:

```text
REAL DATA
   ↓
COMPILE REPRESENTATION
   ↓
FLAT RETRIEVAL ──────┐
                     │
STRUCTURE-AWARE ─────┤
                     ▼
                SAME QUESTIONS
                     │
                     ▼
               SAME EVALUATION
                     │
                     ▼
             QUALITY vs COST
                     │
                     ▼
              H1 DECISION
```

That is the entire purpose of this first build.

---

# 56. What Success Looks Like

A successful H1 experiment might discover something like:

```text
Representation-aware retrieval:

+ similar evidence recall
+ similar evidence precision
+ fewer candidate passages
+ fewer bytes inspected
+ lower latency
+ lower downstream context tokens
+ acceptable indexing overhead
```

But the actual numbers are unknown.

The experiment exists to discover them.

---

# 57. What Failure Looks Like

A valid failure could be:

```text
Structure-aware representation
+
additional indexing
=
negligible retrieval improvement
```

Or:

```text
retrieval work ↓
but evidence recall ↓ significantly
```

Or:

```text
indexing cost dominates
for realistic query volumes
```

These are useful results.

Do not conceal them.

---

# 58. Final H1 Principle

> **Do not build the intelligent filesystem yet. Build the smallest scientifically meaningful experiment that determines whether the representation-before-retrieval idea deserves the intelligent filesystem.**

The long-term StorageOS vision remains in `PRD.md`.

This document controls the first executable experiment.
