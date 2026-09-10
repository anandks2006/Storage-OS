# StorageOS
## Universal Information Navigation, Evidence Indexing, Adaptive Retrieval & Persistent Context Platform

**Document status:** Master Product & Research Requirements Document  
**Target:** Reference implementation / research platform  
**Primary implementation:** Python  
**Primary deployment model:** Local-first, single-user, single-machine initially  
**Scale objective:** From thousands of files on a laptop to arbitrarily large information spaces through adapters and partitioned implementations  
**Core constraint:** Maximum capability with minimum implementation complexity

---

# 1. Executive Summary

StorageOS is a local-first information infrastructure system that builds an **external, immutable, addressable and adaptive representation of arbitrary digital information**.

The original data remains the source of truth and is never silently modified by the indexing or AI subsystems.

StorageOS observes the source, identifies its structure and content, creates only useful derived representations, and stores those representations in a continuously optimized information space containing:

- physical filesystem structure
- logical resource identity
- document structure
- multimodal evidence
- ontology
- entities
- relationships
- hierarchical summaries
- semantic communities
- lexical indexes
- optional vector/late-interaction indexes
- provenance
- versions
- retrieval routes
- locality statistics
- caches
- persistent AI memory
- context state

The fundamental design principle is:

> **Do not optimize retrieval after building a large representation. Construct the representation itself for efficient future retrieval.**

StorageOS therefore treats ingestion as a **Representation Compilation** problem.

It treats retrieval as a **cost-aware navigation/search problem**.

It treats context as a **bounded working memory/cache**, not as the permanent memory of the AI.

It treats AI modification as a **transactional proposal against immutable source data**, rather than granting the AI uncontrolled direct filesystem access.

The project has two simultaneous purposes:

1. **A genuinely useful information-management application.**
2. **A research platform for experimentally determining how far intelligent representation, hierarchical navigation, adaptive indexing, algorithmic search, and persistent context can reduce the cost of AI information retrieval.**

The system will implement relevant ideas from established and recent research—including GraphRAG, RAPTOR, LightRAG, LeanRAG, T-Retriever, ArchRAG, ColBERT and active retrieval approaches—as configurable algorithms and baselines rather than assuming any single technique is universally optimal. GraphRAG uses entities, relationships, hierarchical communities and summaries; RAPTOR builds recursive summary trees; LightRAG combines graph and vector retrieval with incremental updating; LeanRAG explicitly exploits hierarchical semantic aggregation and graph traversal; recent AAAI work such as ArchRAG and T-Retriever further targets hierarchical retrieval, compression and token efficiency.

The project must remain useful even with **zero LLM calls**.

---

# 2. Product Vision

## 2.1 Vision

Create a universal layer through which an AI system can navigate arbitrary digital information using stable logical addresses, hierarchical structure, graph relationships and evidence references rather than repeatedly consuming large quantities of raw context.

The user should be able to point StorageOS at:

- a folder
- a drive
- a USB disk
- a network share
- a NAS
- a cloud-backed filesystem
- a Git repository
- a document collection
- an archive
- an application-specific data source
- eventually databases and other structured systems

and receive a persistent, queryable, optimized representation.

The same protocol should work regardless of whether the underlying information is:

- PDF
- DOCX
- PPTX
- XLSX
- CSV
- TXT
- Markdown
- source code
- image
- audio
- video
- archive
- dataset
- email archive
- database object
- conversation
- AI memory

---

# 3. Core Research Question

StorageOS should experimentally investigate:

> **Can arbitrary digital information be transformed into a persistent, hierarchical, multimodal, provenance-preserving representation whose structure is optimized before and during materialization, such that AI agents can find sufficient trustworthy evidence with substantially lower token, compute, I/O and latency cost than flat or purely vector-based retrieval?**

A second research question is:

> **Can the representation continuously improve through observed usage, making frequently accessed information increasingly cheap to reach without reducing the accessibility or quality of cold information?**

A third is:

> **Can persistent external context allow long-running AI agents to maintain useful task state without continually carrying their entire historical conversation inside the model context window?**

These are hypotheses to test, not claims of superiority that the implementation may assume.

---

# 4. Core Principles

## 4.1 Source immutability

Original source data is the authoritative truth.

Indexing must never:

- rewrite files
- delete files
- rename files
- move files
- silently modify metadata
- overwrite source content

unless an explicit user-approved transaction has been created.

## 4.2 Derived intelligence is disposable

Every index, graph, summary, embedding, cache and learned route is rebuildable derived state.

The system must be capable of destroying and reconstructing derived state from source data.

## 4.3 Identity is independent of physical location

A file or logical object should retain a stable logical identity when:

- moved
- renamed
- reindexed
- migrated
- copied
- relocated between storage systems

where identity can be established safely.

## 4.4 Efficiency by construction

Every representation must have a declared purpose.

Do not materialize an expensive representation merely because it is technically possible.

## 4.5 Lazy computation

Expensive operations must be performed only when justified by:

- expected retrieval value
- observed workload
- explicit user request
- configured importance
- benchmark mode

## 4.6 Multi-resolution representation

Every resource should be navigable from coarse to fine:

```text
space
→ resource
→ document/structural region
→ semantic region
→ evidence
→ exact source location
```

## 4.7 Hybrid retrieval

No single retrieval algorithm is assumed to be optimal.

The planner must be capable of selecting among:

- metadata lookup
- exact/hash lookup
- lexical retrieval
- tree traversal
- graph traversal
- semantic ANN
- late-interaction retrieval
- reranking
- active retrieval
- multimodal analysis

## 4.8 Evidence before generation

The system should optimize for finding **sufficient evidence**, not for retrieving arbitrary chunks.

## 4.9 Context is a working set

The LLM context window is treated as temporary working memory.

Persistent information belongs outside the model.

## 4.10 Cold information remains accessible

Adaptive optimization may make hot information cheaper to access, but must never make cold information effectively disappear.

## 4.11 Provenance is mandatory

Every derived factual claim should be traceable to source evidence where technically possible.

## 4.12 Simple machinery, sophisticated behavior

The reference implementation should prefer:

- one core engine
- one canonical database
- one process initially
- modular adapters
- replaceable algorithms

over unnecessary microservices or infrastructure.

---

# 5. System Architecture

```text
                         SOURCE INFORMATION
                                │
                                ▼
                     SOURCE OBSERVATION LAYER
                                │
                                ▼
                     CONTENT IDENTITY + VERSION
                                │
                                ▼
                     REPRESENTATION COMPILER
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
          STRUCTURE          SEMANTICS         EVIDENCE
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                  OPTIMIZED KNOWLEDGE SPACE
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
  PHYSICAL TREE           SEMANTIC TREE           KNOWLEDGE GRAPH
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
                         MULTI-INDEX LAYER
                                │
       ┌─────────────┬──────────┼──────────────┬─────────────┐
       ▼             ▼          ▼              ▼             ▼
     HASH           FTS      VECTOR       LATE-INT.      ROUTES
       │             │          │              │             │
       └─────────────┴──────────┼──────────────┴─────────────┘
                                ▼
                        QUERY / COST PLANNER
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
          hierarchy           graph              search
              │                 │                  │
              └─────────────────┼──────────────────┘
                                ▼
                    COST-AWARE NAVIGATION
                                │
                         EVIDENCE SELECTION
                                │
                    REDUNDANCY / COVERAGE
                                │
                                ▼
                        CONTEXT COMPILER
                                │
                                ▼
                               LLM
                                │
                 ┌──────────────┴───────────────┐
                 ▼                              ▼
             ANSWER                         ACTION
                 │                              │
                 ▼                              ▼
        MEMORY / FEEDBACK              TRANSACTION PROPOSAL
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
                     LOCALITY OPTIMIZATION
                                │
                                └──────→ future retrieval
```

---

# 6. Canonical Data Model

The entire system should be built around a small number of universal primitives.

## 6.1 Space

An information namespace.

Examples:

```text
C:\
D:\
NAS-01
S3://bucket
Git://repository
Conversation://123
```

## 6.2 Resource

A source object.

Examples:

```text
file
folder
email
database table
video
image
dataset
repository
conversation
```

## 6.3 Node

A logical object within the information graph.

Examples:

```text
folder
document
section
person
organization
concept
project
entity
topic
decision
memory
```

## 6.4 Edge

A typed relationship between nodes.

Examples:

```text
contains
belongs_to
references
authored_by
depends_on
similar_to
derived_from
supports
contradicts
related_to
uses
created_by
```

## 6.5 Evidence

An addressable source-backed fragment.

Examples:

```text
PDF page 12
DOCX paragraph 84
video 01:42:17–01:43:02
image region x/y/w/h
spreadsheet Sheet2!B14:F29
Python lines 84–116
database row
conversation turn
```

## 6.6 Version

A source or derived-state version.

## 6.7 Address

A stable logical reference to an object, region or evidence.

## 6.8 Representation

A derived form optimized for one or more retrieval functions.

## 6.9 RetrievalPlan

A sequence or policy of retrieval operations.

## 6.10 Operation

A user- or agent-proposed action against source data.

---

# 7. Universal Addressing Protocol

## 7.1 Objective

Create a what3words-inspired **compact addressing layer for information**, without making three-word strings the canonical identity.

The addressing system must work for:

- files
- folders
- document regions
- semantic concepts
- graph nodes
- evidence
- memories
- conversations
- external resources

## 7.2 Address layers

### Canonical ID

Stable machine identifier.

```text
uinp://namespace/object-id
```

### Hierarchical semantic coordinate

```text
research/ai/rag/graphrag/section/4
```

### Human-friendly alias

Example:

```text
///forest.rag.graphs
```

The exact word-generation scheme must be independent of any third-party proprietary implementation.

### Physical locator

```text
C:\Research\AI\RAG\paper.pdf
```

All of the above resolve to one logical object.

## 7.3 Address properties

Addresses should support:

- exact resolution
- fuzzy correction
- semantic correction
- aliases
- version references
- snapshots
- historical addresses
- child expansion
- parent resolution
- evidence expansion

Example:

```text
///forest.rag.graphs
///forest.rag.graphs@current
///forest.rag.graphs@snapshot-184
```

## 7.4 Address stability

Physical movement must not automatically invalidate logical references.

---

# 8. Source Observation and Ingestion

## 8.1 Initial observation

On discovery of a source object:

1. record location
2. identify object type
3. collect metadata
4. calculate identity hashes where appropriate
5. assign logical ID
6. identify parser
7. inspect structure
8. plan representations
9. materialize only justified representations
10. record provenance

## 8.2 Change detection

Use:

- file size
- timestamps
- filesystem identity where available
- content hash
- partial hash
- adaptive hashing strategies

Do not fully reprocess unchanged objects.

## 8.3 Incremental processing

When a source changes:

```text
changed source
→ identify affected region
→ identify dependent representations
→ invalidate only affected derived state
→ recompute only affected state
```

## 8.4 Source watcher

Support:

- filesystem events
- polling fallback
- batch reconciliation

Use a durable internal change queue rather than introducing an external message broker.

---

# 9. Representation Compiler

The Representation Compiler is the heart of the efficiency-by-construction principle.

Before expensive indexing occurs, it determines:

- what the object is
- what structure can be obtained cheaply
- what likely query classes apply
- what information can be represented deterministically
- what can be deferred
- what should be materialized
- what can be deduplicated
- what should be summarized
- what should remain lazy

## 9.1 Representation tiers

### Tier 0 — identity

```text
logical ID
path
size
hash
timestamps
type
```

### Tier 1 — structure

```text
pages
headings
sections
slides
cells
functions
classes
scenes
streams
timestamps
```

### Tier 2 — lexical

```text
terms
keywords
FTS
names
dates
numbers
```

### Tier 3 — semantic

```text
topics
entities
concepts
relationships
propositions
```

### Tier 4 — hierarchical

```text
section summaries
document summaries
community summaries
semantic clusters
```

### Tier 5 — deep multimodal

```text
OCR
visual analysis
high-quality transcription
speaker identification
vision-language reasoning
```

Tier 5 must remain lazy whenever possible.

## 9.2 Materialization decision

For representation `R`:

```text
Materialize(R)
iff
ExpectedFutureBenefit(R)
>
StorageCost(R)
+
ComputeCost(R)
+
MaintenanceCost(R)
```

This model may begin heuristic and later become learned.

---

# 10. Multimodal Universal Evidence Model

Every modality must eventually map into the common evidence representation.

## 10.1 PDF

Capture:

- document metadata
- page boundaries
- headings
- paragraphs
- tables
- figures
- references
- page-level evidence
- optional OCR
- optional semantic extraction

## 10.2 DOCX

Capture:

- headings
- paragraphs
- tables
- lists
- links
- document properties
- section hierarchy

## 10.3 PPTX

Capture:

- slide hierarchy
- text boxes
- speaker notes
- images
- charts
- slide order

## 10.4 XLSX / CSV

Capture:

- workbook
- sheets
- ranges
- headers
- cell types
- formulas
- tables
- named ranges
- relationships

Do not flatten a spreadsheet entirely into prose.

## 10.5 Source code

Capture:

- repository
- language
- module
- import graph
- classes
- functions
- methods
- variables where practical
- callers/callees where statically derivable
- line ranges
- dependency relationships
- tests

## 10.6 Images

Capture:

- metadata
- dimensions
- format
- EXIF
- OCR where available
- perceptual hash
- optional captions
- objects
- regions
- visual embeddings

## 10.7 Audio

Capture:

- duration
- codec
- metadata
- channels
- timestamps
- transcript segments
- speakers if available
- topics
- evidence intervals

## 10.8 Video

Capture:

- duration
- streams
- codec
- scene boundaries
- transcript
- speaker segments
- slide transitions
- visual entities
- timestamped evidence

## 10.9 Archives

Index:

```text
ZIP
TAR
7z
RAR where tooling permits
```

without extracting the entire archive unnecessarily.

Archive contents should be logically navigable.

---

# 11. Knowledge Model

## 11.1 Ontology layers

### Core ontology

Universal types:

```text
Person
Organization
Location
Project
Concept
Topic
Document
Image
Video
Audio
Dataset
Software
ProgrammingLanguage
Event
Product
Source
Evidence
Memory
Decision
```

### Domain ontology

Loaded per dataset/domain.

### Learned ontology extensions

Discovered concepts may be proposed but must not silently become authoritative ontology.

## 11.2 Fact classes

Every derived knowledge item must have a type:

```text
EXTRACTED
INFERRED
GENERATED
USER_CONFIRMED
```

## 11.3 Confidence

Record:

- source confidence
- extraction confidence
- inference confidence
- user confirmation state

---

# 12. Knowledge Graph

The graph should initially be stored inside SQLite using normalized node and edge tables.

Minimum fields:

```text
nodes
- id
- type
- label
- summary
- source_reference
- confidence
- created_version
- updated_version

edges
- id
- source_id
- target_id
- relation_type
- confidence
- provenance_id
- created_version
- updated_version
```

No dedicated graph database is required for the reference implementation.

A graph backend interface should exist so a distributed graph engine can be introduced later.

---

# 13. Hierarchical Knowledge Trees

StorageOS must maintain at least:

## 13.1 Physical Tree

```text
drive
→ folder
→ subfolder
→ file
```

## 13.2 Structural Tree

```text
document
→ chapter
→ section
→ paragraph
→ sentence
```

## 13.3 Semantic Tree

```text
domain
→ topic
→ concept
→ entity
→ evidence
```

## 13.4 Community Hierarchy

Build hierarchical semantic communities where useful.

GraphRAG's community-based approach should be implemented as one baseline/option because it explicitly extracts entities and relationships, builds hierarchical communities, and generates bottom-up reports.

---

# 14. Hierarchical Summarization

Support summary levels:

```text
space summary
folder summary
community summary
document summary
section summary
evidence summary
```

Summaries must preserve:

- provenance
- version
- parent relationships
- child references
- confidence
- summary generation method

Do not treat summaries as replacements for source evidence.

RAPTOR-style recursive tree construction should be implemented as an experimental retrieval strategy because its core idea is to recursively cluster, summarize and embed information into multiple levels of a tree so retrieval can occur at different abstraction levels.

---

# 15. Index Layer

The system must support multiple specialized indexes.

## 15.1 Metadata index

Fast lookup for:

- path
- name
- extension
- size
- timestamps
- MIME
- hash

## 15.2 Exact/content hash index

Used for:

- duplicate detection
- identity
- versions
- integrity verification

## 15.3 FTS index

SQLite FTS5 initially.

Used for:

- exact queries
- phrase search
- lexical candidate generation
- verification

## 15.4 Vector index

Optional backend.

The core system must not depend on a particular vector database.

## 15.5 Late-interaction index

Optional experimental backend for ColBERT-style retrieval.

ColBERT is relevant because document representations can be encoded offline and fine-grained query/document interaction can be delayed until retrieval, greatly reducing repeated expensive pairwise processing.

## 15.6 Graph index

Adjacency structures optimized for:

- neighbor traversal
- relation lookup
- reverse lookup
- typed traversal
- graph neighborhoods

## 15.7 Route index

Stores successful retrieval plans and their historical performance.

---

# 16. Cost Model

Every retrieval action should have an estimated cost.

Example:

```text
metadata lookup           0.001
hash lookup               0.001
FTS search                0.002
graph hop                 0.001
tree expansion            0.003
cached route              0.0005
vector ANN                0.02
late interaction          0.03
reranker                  0.10
OCR                       0.50
ASR                       0.80
vision inference          2.00
LLM extraction            5.00
```

These are illustrative initial values, not hard-coded truths.

Cost should include:

```text
CPU
RAM
disk I/O
network
model calls
input tokens
output tokens
latency
storage footprint
```

The system should learn actual costs over time.

---

# 17. Retrieval Planner

The Retrieval Planner receives:

```text
query
current task state
available evidence
token budget
latency budget
compute budget
confidence target
retrieval history
```

and generates a plan.

## 17.1 Candidate operations

```text
metadata_lookup
exact_lookup
fts_search
tree_expand
graph_expand
community_expand
vector_search
late_interaction_search
rerank
retrieve_source
multimodal_analysis
summarize
stop
```

## 17.2 Cost-aware action selection

Initial objective:

```text
priority =
expected_information_gain
× relevance
× evidence_reliability
/
(compute_cost + token_cost + io_cost + latency_cost)
```

The planner should select the action with the highest expected value.

## 17.3 Adaptive stopping

Stop when:

```text
confidence >= target
```

and:

```text
marginal_expected_gain < marginal_cost
```

This eliminates arbitrary fixed `top-k` behavior wherever possible.

---

# 18. Algorithm Laboratory

The retrieval system must have interchangeable planners.

Required implementations/experimental adapters:

1. Greedy
2. Dijkstra
3. A*
4. Weighted A*
5. Best-first search
6. Beam search
7. UCB-style selection
8. Thompson Sampling
9. Set-cover-based evidence selection
10. PCST-style connected evidence selection
11. learned heuristic
12. active retrieval
13. hybrid planner

## 18.1 Dijkstra

Model retrieval as a weighted graph and find minimum-cost paths.

## 18.2 A*

Use:

```text
f(n) = g(n) + h(n)
```

where:

- `g(n)` = cost already incurred
- `h(n)` = estimated remaining cost

## 18.3 Learned heuristic

Learn:

```text
h(query, node)
```

from successful historical retrieval paths.

## 18.4 Beam search

Maintain multiple candidate paths to avoid premature commitment.

## 18.5 Bandit routing

Treat retrieval methods as actions and learn which mechanism works best for a query class.

## 18.6 PCST

Use Prize-Collecting Steiner Tree-style selection when the required evidence is distributed across a graph.

## 18.7 Set cover

Select the smallest-cost evidence set covering the required claim set.

---

# 19. CARVE Experimental Algorithm

Name:

**CARVE — Cost-Aware Retrieval via Evidence**

CARVE is StorageOS's primary experimental retrieval strategy.

For action `a`:

```text
Priority(a) =
ExpectedEvidenceGain(a)
× Relevance(a)
× Reliability(a)
/
Cost(a)
```

where:

```text
Cost(a) =
α TokenCost
+ β ComputeCost
+ γ IOCost
+ δ Latency
+ ε ModelCalls
```

At each step:

1. evaluate candidate operations
2. estimate expected information gain
3. select highest-value operation
4. execute
5. update evidence state
6. update confidence
7. eliminate redundant candidates
8. stop when confidence threshold is reached
9. otherwise repeat

CARVE must remain fully benchmarkable against the other algorithms.

---

# 20. Information-Theoretic Retrieval

The system should estimate marginal information gain.

Given already-selected evidence `E`:

```text MarginalValue(x)
=
InformationGain(x | E)
```

Evidence that adds little new information should receive lower priority.

This reduces:

- repeated claims
- redundant chunks
- duplicate summaries
- unnecessary context

---

# 21. Evidence Selection

The final evidence set should optimize:

```text coverage
+
relevance
+
authority
+
provenance quality
+
diversity
-
redundancy
-
token cost
```

The engine should be able to use:

- greedy set cover
- weighted set cover heuristics
- PCST-like selection
- diversity-aware selection

---

# 22. Context Compiler

This is one of StorageOS's most important components.

The Context Compiler turns:

```text persistent knowledge
+
current task
+
retrieved evidence
+
known state
+
token budget
```

into:

```text minimal sufficient model context
```

## 22.1 Context must not equal conversation history

Never blindly send the full conversation.

Instead compile:

```text task state
active decisions
required prior facts
relevant evidence
current unresolved questions
new information
```

## 22.2 Delta context

Maintain:

```text Context(t+1)
=
Context(t)
+
new_required_information
-
redundant_information
-
invalidated_information
```

## 22.3 Known-state compression

If a proposition is already established:

```text fact_1842 = confirmed
```

do not repeatedly transmit the full supporting text unless verification is required.

## 22.4 Evidence pointers

Context may contain:

```text
///storage.retrieval.architecture
```

rather than the entire underlying representation.

The model can request expansion.

---

# 23. Persistent AI Context Memory

Treat conversations as indexed information sources.

A conversation becomes:

```text Conversation
 ├── task
 ├── topics
 ├── facts
 ├── decisions
 ├── questions
 ├── evidence
 ├── hypotheses
 ├── conclusions
 └── unresolved items
```

## 23.1 Memory classes

```text episodic
semantic
procedural
decision
task-state
evidence-linked
```

## 23.2 Memory confidence

```text source-backed
user-confirmed
model-generated
inferred
temporary
```

## 23.3 Memory invalidation

A memory linked to obsolete source evidence must be:

- invalidated
- downgraded
- or recomputed

rather than silently retained.

---

# 24. Context Virtual Memory

Treat model context as a cache.

```text HOT
current reasoning state

WARM
active task knowledge

COOL
recent evidence

COLD
persistent memory
```

When context pressure rises:

```text low-value active state
→ persist externally
→ evict from context
```

When required:

```text retrieve
→ compile
→ reinsert
```

Critical invariant:

> Evicted context is not forgotten; it becomes externally addressable persistent state.

This is the proposed **Context Virtual Memory** subsystem.

---

# 25. Semantic Locality Engine

StorageOS must learn information access patterns.

Track:

```text frequency
recency
query class
successful retrieval routes
evidence usefulness
route reuse
access cost
future-use probability
```

For information node `x`:

```text Locality(x)
=
w1 Frequency
+
w2 Recency
+
w3 Utility
+
w4 RouteReuse
+
w5 PredictedFutureUse
```

The coefficients must be configurable and later learnable.

---

# 26. Adaptive Representation Promotion

A node may progress:

```text COLD
 ↓
WARM
 ↓
HOT
```

but promotion means:

- faster indexes
- precomputed summaries
- cached graph neighborhoods
- cached retrieval routes
- physically clustered metadata
- context-ready evidence

It does **not** mean altering the source file.

## 26.1 Semantic locality

Locality should be query-conditioned.

Example:

```text
Document A

RAG queries:       0.94
Python queries:    0.04
Finance queries:   0.00
```

This is more useful than simple LRU.

---

# 27. Route Learning

Cache:

```text query/query-class
→ retrieval plan
→ successful route
→ evidence
→ observed outcome
```

Do not simply cache answers.

A route should only be reused when source versions and relevant evidence remain valid.

---

# 28. Semantic Prefetching

StorageOS may predict future retrieval needs.

Prefetch only when:

```text P(next use)
× ExpectedBenefit
>
PrefetchCost
```

Possible prefetch targets:

- graph neighborhoods
- summaries
- lexical postings
- embeddings
- evidence records
- context state

Prefetching must never become uncontrolled background computation.

---

# 29. Learned Information Topology

Frequently traversed regions may acquire:

- shortcut edges
- materialized views
- compact aggregate representations
- cached neighborhoods
- optimized physical ordering

Cold regions retain their standard indexes and fallback search path.

The optimized topology is a derived acceleration structure.

---

# 30. Fast Path / Complete Path

Every retrieval must retain a fallback.

```text FAST PATH
optimized route
    ↓
evidence
```

If confidence is inadequate:

```text FULL PATH
broader exploration
```

Therefore:

> Optimization improves latency; it does not remove completeness.

---

# 31. Any-Time Retrieval

Retrieval should be capable of returning increasingly strong results under increasing budgets.

Example:

```text 10 ms    preliminary candidates
30 ms        probable evidence
100 ms       validated evidence
500 ms       deep retrieval
2 sec        multimodal analysis
10 sec       exhaustive investigation
```

The exact targets depend on hardware and workload.

---

# 32. AI Navigation Protocol

The AI-facing interface should expose high-level operations rather than filesystem primitives.

Minimum API:

```text resolve(address)
inspect(address)
navigate(address)
expand(address, depth)
children(address)
parent(address)
neighbors(address)
search(query)
search_exact(query)
search_semantic(query)
search_lexical(query)
evidence(address)
source(address)
history(address)
compare(address_a, address_b)
context(query, budget)
memory(query, budget)
propose_change(address, operation)
```

The agent should not receive unrestricted:

```text os.remove()
os.rename()
shutil.move()
```

as fundamental tools.

---

# 33. AI-Safe Operations

AI modifications must use:

```text propose
→ validate
→ preview
→ impact analysis
→ user approval
→ transaction
→ snapshot
→ execute
→ verify
→ index update
```

Supported proposals:

```text create
rename
move
delete
merge
copy
tag
annotate
generate
modify
```

## 33.1 Transaction record

Must contain:

```text operation ID
source snapshot
target node
requested action
actor
timestamp
reason
evidence
affected objects
rollback information
result
```

---

# 34. Snapshot and Version System

Every significant source mutation should be associated with a snapshot.

Support:

```text current
previous
snapshot ID
date/time
file version
knowledge version
```

Allow comparison:

```text snapshot A
vs
snapshot B
```

including:

- files added
- files deleted
- files changed
- relationships changed
- summaries changed
- knowledge invalidated

---

# 35. Duplicate Intelligence

Support progressively expensive duplicate detection:

```text name/size
→ metadata
→ partial hash
→ full hash
```

Duplicate groups must show:

- source files
- exact duplicate status
- size
- reclaimable space
- version relationship

Never delete automatically.

---

# 36. Similarity Intelligence

Optional modules:

- visually similar images
- screenshots
- resized images
- recompressed images
- near-duplicate documents
- similar semantic documents

Similarity results must not be confused with exact duplicates.

---

# 37. Storage Intelligence

StorageOS must provide:

## Drive overview

- total
- used
- free
- filesystem
- drive type
- utilization

## Directory analysis

- largest folders
- largest files
- growth
- age
- access frequency

## File categories

```text
documents
images
video
audio
archives
executables
installers
code
datasets
models
logs
temporary
unknown
```

## Developer analyzer

Detect:

```text
node_modules
.git
venv
.venv
Conda
pip cache
npm cache
Docker data
Jupyter
Hugging Face cache
VS Code data
model checkpoints
```

## Cleanup advisor

Potential candidates:

- temporary files
- caches
- duplicate files
- obsolete installers
- crash dumps
- logs

All cleanup recommendations require preview and explicit approval.

---

# 38. Storage History

Record:

```text timestamp
used bytes
free bytes
top growth locations
new large files
deleted files
growth trends
```

Enable:

```text "What caused my C: drive to lose 20 GB this week?"
```

---

# 39. Real-Time Monitoring

Support:

```text create
modify
delete
rename
move
```

events.

The system should update derived state incrementally.

---

# 40. Alerts

Allow:

```text drive > threshold
folder grows rapidly
new huge file
unexpected growth
duplicate explosion
model cache growth
```

---

# 41. Search

Search should support:

### Exact

```text filename
path
hash
phrase
identifier
```

### Structured

```text type
size
date
location
author
extension
```

### Semantic

```text "papers about hierarchical retrieval"
```

### Relational

```text "documents connected to StorageOS"
```

### Multimodal

```text "videos where the speaker explains graph traversal"
```

### Hybrid

Combine all applicable methods.

---

# 42. Benchmark Corpus

The repository must contain a synthetic and real-world-style benchmark corpus.

It should include:

```text nested folders
duplicate files
near duplicates
PDFs
DOCX
PPTX
XLSX
CSV
Markdown
source code
images
audio
video
archives
mixed projects
cross-referencing documents
contradictory documents
dated versions
conversation logs
```

The benchmark must contain known ground truth.

---

# 43. Benchmark Query Classes

At minimum:

## Q1 — exact

> Find the file named X.

## Q2 — lexical

> Find documents containing phrase X.

## Q3 — semantic

> Find material about concept X.

## Q4 — hierarchical

> What are the main themes in this collection?

## Q5 — relational

> Which papers are connected to project X?

## Q6 — multi-hop

> Which author wrote papers that influenced project X?

## Q7 — temporal

> What did the information space say about X before date Y?

## Q8 — multimodal

> What part of this lecture discusses X?

## Q9 — evidence

> Where exactly does the source support claim X?

## Q10 — conversational

> Continue what we were discussing about X three hours ago.

## Q11 — context reconstruction

> Recover the decisions that led to the current architecture.

## Q12 — destructive-action verification

> Which files can safely be removed?

---

# 44. Evaluation Metrics

Every benchmark run should report:

## Retrieval

- Recall@k
- evidence recall
- evidence precision
- MRR
- nDCG where meaningful
- number of nodes explored
- number of source objects touched

## Generation

- answer correctness
- groundedness
- citation correctness
- hallucination rate

## Resource usage

- input tokens
- output tokens
- total tokens
- model calls
- embedding calls
- OCR calls
- ASR calls
- CPU time
- RAM
- disk reads
- disk writes
- index size
- network usage

## Performance

- cold latency
- warm latency
- P50
- P95
- P99 where measurable

## Maintenance

- initial indexing time
- incremental update time
- changed-object count
- invalidated-node count
- rebuild time

## Efficiency

Primary derived metrics:

```text useful_evidence / token
useful_evidence / compute
useful_evidence / latency
answer_quality / token
answer_quality / retrieval_cost
```

---

# 45. Baseline Experiments

For the same corpus and same model, compare:

```text B0: raw filesystem + LLM
B1: lexical RAG
B2: vector RAG
B3: hybrid lexical + vector
B4: RAPTOR-style hierarchy
B5: GraphRAG-style communities
B6: LightRAG-style graph + vector
B7: LeanRAG-style hierarchical graph retrieval
B8: ArchRAG-style attributed community hierarchy
B9: T-Retriever-style tree/structural retrieval
B10: ColBERT-style late interaction
B11: active retrieval
B12: CARVE
B13: CARVE + locality
B14: CARVE + locality + context compiler
```

The system must preserve reproducibility.

---

# 46. Ablation Studies

Required experiments:

### No hierarchy

Measure effect of hierarchy.

### No graph

Measure effect of graph reasoning.

### No lexical

Measure effect of exact retrieval.

### No vector

Measure how much semantic indexing adds.

### No locality

Measure long-term adaptive optimization.

### No route cache

Measure retrieval-plan reuse.

### No context compiler

Measure context/token cost.

### No learned heuristic

Compare A* with and without learned routing.

### No predictive prefetch

Measure prefetch utility.

### Full indexing vs lazy indexing

Measure computation saved by progressive materialization.

---

# 47. Efficiency-By-Construction Experiment

This is a central experiment.

Compare:

## System A

```text ingest everything
→ produce maximal indexes
→ optimize retrieval later
```

with:

## StorageOS

```text inspect
→ plan representation
→ optimize representation
→ materialize
→ retrieve
```

Compare:

```text index size
indexing compute
initial tokens
retrieval latency
query tokens
maintenance cost
answer quality
```

This directly tests the central thesis of the project.

---

# 48. Self-Optimization Experiment

Run a long synthetic workload.

Initially:

```text random query distribution
```

Then gradually shift to repeated user behavior.

Measure whether:

```text route cost
retrieval latency
tokens
model calls
```

decrease over time.

The desired outcome is:

```text usage
 ↓
learn locality
 ↓
materialize beneficial shortcuts
 ↓
lower future retrieval cost
```

while:

```text cold-data recall ≈ unchanged
```

---

# 49. Context-Pressure Benchmark

Create conversations of increasing length:

```text 10 turns
50 turns
100 turns
250 turns
500 turns
1000 turns
```

Compare:

```text full-history prompting
summary-only memory
naive RAG memory
StorageOS persistent context
```

Measure:

- historical fact recall
- decision recall
- evidence grounding
- token consumption
- context latency
- contradiction rate

Test specifically for the “lost in the middle” problem, where relevant information can become harder to use as context length grows.

---

# 50. Context Virtual Memory Benchmark

Simulate a model with a constrained context budget.

Example budgets:

```text 2K
4K
8K
16K
32K tokens
```

StorageOS must attempt to preserve task continuity by:

```text externalizing state
evicting low-value context
retrieving needed state
recompiling context
```

Measure whether task performance can be maintained as active context remains bounded.

---

# 51. Multimodal Retrieval Benchmark

Example:

```text 2-hour lecture video
500-page PDF
100-slide presentation
100 images
100 audio files
```

Queries should require:

- transcript
- visual evidence
- document structure
- relationships
- timestamps

Compare:

```text full transcription
full multimodal indexing
query-driven analysis
StorageOS adaptive routing
```

---

# 52. Storage-Efficient Physical Layout

Derived data should itself be optimized.

Prefer:

- normalized records
- integer IDs
- compact references
- compressed text where appropriate
- deduplicated summaries
- shared evidence objects
- clustered frequently traversed records
- append-friendly version records

Do not duplicate the same content into multiple indexes unless the measurable retrieval benefit justifies the cost.

---

# 53. Canonical vs Materialized Data

Separate:

## Canonical derived state

Must be sufficient to rebuild other derived structures.

## Materialized acceleration structures

Examples:

```text vector indexes
route caches
hot-node caches
community reports
prefetched neighborhoods
```

Materialized data may be deleted and rebuilt.

This distinction is mandatory.

---

# 54. Security and Safety

## Source access

StorageOS requires explicit access to each source space.

## AI permissions

Permission classes:

```text READ
SEARCH
PROPOSE
WRITE
DELETE
ADMIN
```

Default AI permission:

```text READ + SEARCH + PROPOSE
```

Never default to unrestricted destructive operations.

## Sensitive data

The system should permit exclusion rules:

```text folder exclusions
extension exclusions
path patterns
maximum file size
privacy tags
```

---

# 55. Privacy

Default architecture:

```text local indexing
local metadata
local graph
local FTS
local caches
```

LLM calls should be:

```text optional
configurable
auditable
explicit
```

Remote model use must be visible.

The system must clearly identify when source content leaves the local environment.

---

# 56. LLM Integration

StorageOS must not depend on one LLM provider.

Provider abstraction:

```text local model
OpenAI-compatible endpoint
Groq
other API provider
```

LLM functions should include:

```text summarization
entity extraction
relationship proposal
classification
question decomposition
retrieval planning
context compression
memory extraction
multimodal reasoning
```

Each function should have:

- model selection
- token budget
- timeout
- retry policy
- cache
- provenance

Groq/Qwen can be used for the initial experimental environment, but deterministic mechanisms must remain functional without it.

---

# 57. Embedding Architecture

Embeddings must be optional and pluggable.

The system must distinguish:

```text embedding model
embedding version
embedding dimensionality
source version
index version
```

Changing embedding models should invalidate only affected indexes rather than requiring source reprocessing.

---

# 58. Caching Architecture

Required caches:

### Identity cache

```text path → identity
```

### Structural cache

```text resource → structure
```

### Query-route cache

```text query class → route
```

### Evidence cache

```text validated query → evidence set
```

### Context cache

```text task state → compiled context
```

### Model-result cache

Only where source-version validity can be established.

---

# 59. Cache Invalidation

Every cache entry must carry dependency information.

Example:

```text cache entry
  ↓
evidence IDs
  ↓
source versions
```

If source version changes:

```text invalidate dependent cache
```

Do not rely on time-based expiration alone.

---

# 60. AI Memory Graph

Conversations should use the same universal primitives as files.

For example:

```text Conversation
→ Node: decision
→ Node: project
→ Node: concept
→ Evidence: conversation turn
```

No separate incompatible “memory architecture.”

---

# 61. Context State Object

The current task should have a compact state object:

```text
TaskState
- goal
- constraints
- confirmed_facts
- active_concepts
- decisions
- unresolved_questions
- current_addresses
- retrieved_evidence
- source_versions
- next_actions
```

This state should be persistent and independently retrievable.

---

# 62. Semantic Address Usage in Context

Instead of repeating long paths:

```text
C:\Users\...\Research\Artificial Intelligence\...
```

the model may reference:

```text
///forest.rag.graphs
```

and expand only when required.

This reduces repeated descriptive context and makes references stable.

---

# 63. Query Planner Memory

The planner should learn:

```text query class
→ likely domain
→ likely namespace
→ likely retrieval algorithm
→ likely starting node
→ likely successful path
```

Example:

```text
"where did I save..."
→ filesystem + metadata

"what does this paper say..."
→ document hierarchy + lexical

"how are X and Y related..."
→ graph

"what did the lecture show..."
→ video evidence

"why did we choose..."
→ conversation memory + decisions + evidence
```

---

# 64. Self-Optimization Feedback Loop

```text
query
 ↓
retrieval plan
 ↓
execution
 ↓
evidence
 ↓
answer
 ↓
usefulness assessment
 ↓
route statistics
 ↓
locality update
 ↓
representation decisions
 ↓
future query
```

The system should learn from:

- successful retrieval
- failed retrieval
- user corrections
- source selection
- answer validation
- query repetition
- retrieval latency
- token cost

---

# 65. User Feedback

Useful signals include:

```text explicitly selected result
opened source
expanded node
rejected result
corrected answer
asked follow-up
approved operation
rejected operation
```

These signals may influence retrieval quality and locality.

Do not treat silence as positive feedback.

---

# 66. Contradiction Handling

When multiple sources disagree:

```text claim A
source 1
confidence

claim B
source 2
confidence
```

the system must not collapse them into a single false fact.

Represent:

```text supports
contradicts
supersedes
uncertain
```

with provenance and source versions.

---

# 67. Temporal Knowledge

Support:

```text valid_from
valid_to
observed_at
source_version
```

Example query:

> What did my knowledge base indicate in June 2025?

The answer should use historically valid representations rather than current state only.

---

# 68. Physical Storage Optimization

The derived index should be able to use storage tiers.

Conceptually:

```text HOT
RAM / local cache

WARM
SSD / frequently accessed DB pages

COOL
normal local index

COLD
compressed / lazy-derived metadata
```

These are implementation strategies, not changes to source truth.

---

# 69. Distributed/Scale-Agnostic Protocol

The protocol must not assume:

- Windows
- local disk
- SQLite
- a particular vector DB
- one machine

The reference implementation can use those.

Future adapters may support:

```text SMB/NFS
NAS
S3/object storage
cloud file stores
Git
databases
enterprise repositories
```

The same logical model should apply.

---

# 70. Adapter Interface

Each source adapter should implement approximately:

```python
discover()
identify()
stat()
read_metadata()
read_structure()
read_content()
watch()
locate()
version()
```

The adapter should return canonical StorageOS objects rather than leaking source-specific representations into the core.

---

# 71. Minimal-Coupling Architecture

The application must avoid unnecessary independent services.

Default implementation:

```text one Python application
one SQLite database
filesystem-backed derived artifacts
in-process caches
plugin adapters
FastAPI interface
CLI
web UI
```

No mandatory:

```text Neo4j
Redis
Kafka
PostgreSQL
Kubernetes
microservices
message broker
cloud service
```

Advanced infrastructure may be added as optional adapters later.

---

# 72. Canonical Persistence

SQLite should initially contain:

```text spaces
resources
versions
nodes
edges
evidence
provenance
summaries
communities
indexes
routes
query_history
locality
memory
task_state
operations
snapshots
```

Large binary derived artifacts may live outside SQLite and be referenced by content IDs.

---

# 73. CLI

Required commands:

```text
storageos scan <source>
storageos rescan <source>
storageos status
storageos tree
storageos search <query>
storageos resolve <address>
storageos inspect <address>
storageos navigate <query>
storageos evidence <address>
storageos context <query>
storageos memory <query>
storageos duplicates
storageos large-files
storageos history
storageos snapshot
storageos diff
storageos propose
storageos apply
storageos benchmark
storageos evaluate
storageos doctor
```

---

# 74. REST API

FastAPI reference API.

Endpoints should cover:

```text /spaces
 /resources
 /nodes
 /addresses
 /search
 /navigate
 /evidence
 /context
 /memory
 /history
 /snapshots
 /operations
 /benchmarks
 /metrics
```

WebSockets may be used for:

- indexing progress
- watcher events
- job progress

---

# 75. Web Dashboard

The dashboard should visualize:

## Storage

- drive capacity
- folder size
- growth

## Knowledge

- semantic tree
- graph
- entities
- communities

## Retrieval

- query route
- nodes explored
- evidence selected
- cost breakdown
- token usage

## Locality

- hot regions
- route popularity
- promotion/demotion

## Context

- current working set
- evicted memory
- retrieved memories
- context budget

## Provenance

- claim
- supporting evidence
- source location
- version

## Operations

- proposed change
- impact
- approval
- execution
- rollback

---

# 76. Research Visualization

A dedicated diagnostic screen should show:

```text Query
 ↓
Planner
 ↓
Candidate actions
 ↓
Chosen route
 ↓
Nodes visited
 ↓
Evidence selected
 ↓
Tokens
 ↓
Final context
```

This is essential for debugging the research algorithms.

---

# 77. Implementation Stack

Recommended reference stack:

```text Python 3.12+
FastAPI
Uvicorn
Pydantic
SQLite
SQLite FTS5
Typer
pytest
watchdog
psutil
pathlib
hashlib
```

Format libraries should be added only where needed.

Potential adapters:

```text pypdf
python-docx
openpyxl
python-pptx
markdown parsers
Pillow
ffmpeg
Whisper-compatible ASR
OCR backend
tree-sitter
```

All advanced dependencies should be optional where possible.

---

# 78. Package Design

Recommended repository:

```text
storageos/
│
├── core/
│   ├── models.py
│   ├── identity.py
│   ├── versions.py
│   ├── provenance.py
│   └── config.py
│
├── spaces/
│   ├── manager.py
│   └── adapters/
│
├── ingest/
│   ├── pipeline.py
│   ├── change_queue.py
│   ├── hashing.py
│   └── representation.py
│
├── parsers/
│   ├── documents.py
│   ├── spreadsheets.py
│   ├── presentations.py
│   ├── code.py
│   ├── image.py
│   ├── audio.py
│   ├── video.py
│   └── archives.py
│
├── knowledge/
│   ├── ontology.py
│   ├── graph.py
│   ├── hierarchy.py
│   ├── communities.py
│   └── evidence.py
│
├── indexes/
│   ├── metadata.py
│   ├── fts.py
│   ├── vector.py
│   ├── late_interaction.py
│   ├── graph.py
│   └── routes.py
│
├── retrieval/
│   ├── planner.py
│   ├── costs.py
│   ├── dijkstra.py
│   ├── astar.py
│   ├── beam.py
│   ├── bandit.py
│   ├── pcst.py
│   ├── setcover.py
│   ├── carve.py
│   ├── rerank.py
│   └── stopping.py
│
├── context/
│   ├── compiler.py
│   ├── state.py
│   ├── memory.py
│   ├── delta.py
│   └── virtual_memory.py
│
├── locality/
│   ├── scoring.py
│   ├── promotion.py
│   ├── routing.py
│   └── prefetch.py
│
├── addresses/
│   ├── canonical.py
│   ├── human.py
│   ├── resolver.py
│   └── fuzzy.py
│
├── operations/
│   ├── proposals.py
│   ├── validation.py
│   ├── transactions.py
│   ├── snapshots.py
│   └── rollback.py
│
├── storage/
│   ├── database.py
│   ├── repositories.py
│   └── artifacts.py
│
├── interfaces/
│   ├── cli.py
│   ├── api.py
│   └── web/
│
├── benchmark/
│   ├── datasets/
│   ├── queries/
│   ├── runners.py
│   ├── metrics.py
│   └── reports.py
│
└── tests/
```

---

# 79. Complexity-Control Requirements

This is mandatory.

## 79.1 No feature duplication

Different modalities must converge into common primitives.

## 79.2 No mandatory external infrastructure

The reference system must run locally.

## 79.3 No algorithm-specific core assumptions

Planner interfaces must allow multiple algorithms.

## 79.4 No provider-specific AI logic

LLM provider abstraction is mandatory.

## 79.5 No source duplication

The system should not copy the user's entire filesystem merely to make it searchable.

## 79.6 No mandatory vector database

Vector retrieval is an optional index.

## 79.7 No mandatory graph database

Graph data initially lives in SQLite.

## 79.8 No separate memory system

Conversation memory uses the same core information model.

## 79.9 No separate semantic addressing database

Addresses resolve against canonical node identity.

---

# 80. Correctness Invariants

The implementation must enforce:

### Source integrity

```text
Indexing does not modify source.
```

### Provenance

```text
Derived factual claims should point to evidence.
```

### Rebuildability

```text Derived state can be rebuilt from source.
```

### Version correctness

```text Cached knowledge must not silently cross source versions.
```

### Fallback completeness

```text Optimized path cannot permanently hide cold information.
```

### Permission safety

```text AI cannot perform destructive operations without explicit authorization.
```

### Deterministic identity where possible

```text Same source/version should produce stable identifiers.
```

---

# 81. Performance Targets

Initial target goals for a typical modern laptop:

- metadata lookup: near-instantaneous
- FTS search: interactive
- graph traversal: interactive
- address resolution: interactive
- warm retrieval: sub-second where practical
- expensive AI operations: explicitly surfaced and measurable
- incremental indexing: proportional to changed data rather than total corpus

Do not sacrifice correctness to hit arbitrary latency numbers.

Benchmark actual hardware and report results.

---

# 82. Testing Strategy

## Unit tests

Every core primitive.

## Integration tests

Full:

```text source
→ ingest
→ representation
→ indexes
→ retrieval
→ evidence
→ context
```

## Mutation tests

Verify changes only invalidate necessary derived structures.

## Corruption tests

Delete derived state and rebuild.

## Crash recovery

Interrupt indexing and restart.

## Version tests

Change source and verify stale caches are invalidated.

## Safety tests

Verify AI cannot bypass transactional operations.

## Adversarial retrieval tests

Include:

- misleading filenames
- semantically similar irrelevant documents
- duplicated information
- contradictory sources
- deeply buried evidence
- irrelevant popular documents
- old outdated versions

---

# 83. Fault Tolerance

If one parser fails:

```text do not stop the entire index
```

Record:

```text resource
parser
error
timestamp
retry state
```

If an LLM call fails:

```text use deterministic representations
```

If embeddings fail:

```text FTS + graph + hierarchy remain usable
```

If the index database becomes corrupt:

```text rebuild from source + snapshots
```

---

# 84. Offline-First Requirement

The system must provide substantial functionality with:

```text no network
no API keys
no LLM
no cloud service
```

Minimum offline functionality:

```text filesystem indexing
metadata
hashes
duplicates
FTS
document structure
basic graph
addresses
provenance
snapshots
search
basic navigation
```

---

# 85. Experimental LLM Layer

LLM-powered capabilities should include:

```text entity extraction
relationship extraction
topic classification
semantic summarization
query decomposition
retrieval-plan assistance
memory extraction
context compression
multimodal reasoning
```

All LLM-derived objects must record:

```text model
model version
prompt/version
timestamp
input source versions
output hash
confidence
```

---

# 86. External Research Implementations

The project must not reinvent established techniques when a published approach is useful.

At minimum, implement or faithfully prototype the following classes.

### GraphRAG

Use its graph extraction, community hierarchy and summary concepts as one benchmark/reference pathway. Microsoft GraphRAG explicitly supports global, local, DRIFT and basic search modes over graph/community structures.

### RAPTOR

Implement recursive summary/tree retrieval as an alternative hierarchical representation.

### LightRAG

Prototype graph + vector dual-level retrieval and incremental update ideas.

### LeanRAG

Implement semantic aggregation and structure-guided hierarchical traversal as an experimental planner/representation.

### ArchRAG

Prototype attributed community hierarchical indexing where applicable, particularly for token-aware community retrieval.

### T-Retriever

Prototype semantic-structural tree construction and adaptive compression concepts.

### ColBERT-style retrieval

Prototype late-interaction retrieval as an optional neural retrieval tier.

### Active retrieval / FLARE-style behavior

Prototype retrieval triggered by uncertainty during generation rather than fixed retrieval before generation.

These implementations should be treated as **research modules and baselines**, not automatically as the production default.

---

# 87. Novel StorageOS Research Layer

The system's primary experimental contribution should be the combination of:

```text
Representation Compiler
+
Cost-Aware Retrieval
+
Semantic Locality
+
Adaptive Materialization
+
Stable Semantic Addressing
+
Context Virtual Memory
+
Persistent Context Compilation
+
Unified multimodal evidence model
+
Immutable source layer
```

The system must explicitly distinguish:

```text prior research technique
vs
StorageOS integration
vs
new experimental algorithm
```

in benchmark reports.

---

# 88. Proposed Novel Concepts

## 88.1 Representation Compiler

Optimize the information representation before materialization.

## 88.2 CARVE

Cost-aware evidence acquisition.

## 88.3 Semantic Locality

Learn where useful information tends to occur and make derived access paths cheaper.

## 88.4 Semantic Fast Lanes

Persist optimized frequently traversed routes through the knowledge graph.

## 88.5 Context Virtual Memory

External persistent context with bounded active context.

## 88.6 Delta Context

Transmit only changes to working context.

## 88.7 Evidence Addressing

Give source-grounded information stable compact addresses.

## 88.8 Universal Information Navigation Protocol

Abstract logical navigation away from physical storage implementations.

---

# 89. Theoretical Optimization Objective

Primary optimization objective:

```text
maximize:

EvidenceQuality
× RetrievalRecall
× Grounding
× ContextUtility

while minimizing:

StorageCost
+
IndexingCost
+
ComputeCost
+
DiskIO
+
NetworkCost
+
TokenCost
+
Latency
```

One simplified objective:

```text
J =
(EvidenceQuality × Recall × ProvenanceStrength × ContextUtility)
/
(Storage + Compute + IO + Tokens + Latency)
```

Subject to:

```text
SourceIntegrity = 1

Confidence >= target

TokenUsage <= budget

PermissionViolations = 0
```

---

# 90. Retrieval as a Search Problem

Define the information space as a graph:

```text G = (V, E)
```

where:

```text V = information states / nodes
E = navigation or processing actions
```

Each edge has a cost:

```text c(e)
```

Each node has:

```text relevance
evidence value
confidence
```

The retrieval problem becomes:

> Find a path or connected subgraph that obtains sufficient trustworthy evidence at minimum expected cost.

This allows:

```text shortest-path methods
heuristic search
stochastic search
bandit selection
subgraph optimization
learned routing
```

to be compared under one framework.

---

# 91. Retrieval State

The planner's state should include:

```text query
candidate nodes
known facts
retrieved evidence
confidence
remaining token budget
remaining compute budget
remaining latency budget
source versions
history
```

An action may be:

```text search
expand
traverse
retrieve
rerank
inspect
analyze
stop
```

---

# 92. Information Gain Estimation

The system should estimate:

```text
ExpectedGain(action)
```

using:

- historical query outcomes
- node statistics
- graph structure
- semantic similarity
- lexical overlap
- source authority
- uncertainty

Initial implementations can use heuristics.

Future implementations may learn the estimator.

---

# 93. Learning Loop

```text initial heuristics
       ↓
observed query workload
       ↓
retrieval statistics
       ↓
learned costs
       ↓
learned heuristics
       ↓
improved routes
       ↓
revised locality
       ↓
better representation materialization
```

The system should not require reinforcement learning to function.

RL/bandits are optional research experiments.

---

# 94. Context Compilation Algorithm

Given:

```text TaskState
EvidenceSet
MemorySet
TokenBudget
```

perform:

1. identify required state
2. retrieve supporting evidence
3. remove redundant evidence
4. prefer high-authority evidence
5. preserve source references
6. compress where safe
7. inject semantic addresses
8. include unresolved uncertainty
9. produce final context
10. record what was omitted

The compiler should produce a machine-readable manifest describing what was included.

---

# 95. Context Budget Allocation

Allocate tokens across:

```text task state
prior decisions
new evidence
source excerpts
instructions
tool outputs
```

Use dynamic allocation rather than fixed percentages.

High-confidence known facts consume almost no repeated context.

Uncertain/new facts receive more evidence budget.

---

# 96. Context Reconstruction

Given:

```text task ID
```

the system should be able to reconstruct:

```text current state
required historical decisions
relevant evidence
important prior questions
active source versions
```

without replaying the entire conversation.

---

# 97. Long-Running Agent Mode

StorageOS should support a hypothetical agent operating for:

```text hours
days
weeks
```

without requiring the entire historical conversation to stay in context.

The agent should instead carry:

```text task identifier
current state
semantic addresses
small working context
```

and retrieve previous knowledge as needed.

---

# 98. Context Expiration

Not all information should survive forever at equal priority.

Classify state:

```text permanent
long-term
task-scoped
session-scoped
temporary
```

Expiration should remove active representations, not source evidence.

---

# 99. Knowledge Quality

The system should expose:

```text evidence-backed
inferred
uncertain
contradictory
stale
unverified
user-confirmed
```

A retrieval result should not simply be:

```text relevance = 0.91
```

It should expose:

```text relevance
evidence strength
freshness
provenance
confidence
```

---

# 100. User Experience Philosophy

The system should make sophisticated optimization invisible.

The user should not need to know:

```text what was cached
what was promoted
which algorithm ran
which graph path was used
```

unless viewing diagnostics.

The system should simply become faster.

A frequently accessed region may silently acquire acceleration structures.

Cold data remains available through normal fallback paths.

---

# 101. Example User Flow

User indexes:

```text C:\
```

StorageOS creates:

```text C:\
├── Users
├── Projects
├── Research
├── Media
└── Downloads
```

The system creates corresponding semantic structures.

User asks:

> Which papers influenced the design of StorageOS?

StorageOS might execute:

```text query decomposition
→ Research / Projects candidate regions
→ semantic concepts
→ graph traversal
→ hierarchy pruning
→ lexical verification
→ evidence selection
→ context compilation
```

The model receives perhaps:

```text active task
3–7 relevant evidence fragments
source addresses
key relationships
```

rather than an enormous corpus dump.

---

# 102. Example Semantic Address

```text
///forest.rag.graphs
```

may resolve to:

```text logical node:
GraphRAG / hierarchical retrieval cluster
```

The node may point to:

```text papers
notes
projects
conversation decisions
specific evidence
```

The physical location is resolved only when necessary.

---

# 103. Example Adaptive Behavior

First query:

```text "What is GraphRAG?"
```

System searches:

```text FTS
→ hierarchy
→ vector
```

After repeated related queries:

```text GraphRAG
↔ StorageOS
↔ hierarchical retrieval
```

becomes a hot semantic region.

The system may create:

```text cached neighborhood
cached summary
cached route
optimized records
```

Later query:

```text "Why did we choose hierarchical retrieval?"
```

may execute:

```text route cache
→ decision memory
→ GraphRAG region
→ supporting evidence
```

with significantly less work.

---

# 104. Example Context Recovery

After hundreds of conversation turns:

User:

> Continue what we decided about the retrieval engine.

StorageOS should resolve:

```text task state
→ retrieval architecture
→ previous decisions
→ unresolved questions
→ relevant evidence
```

and produce a compact working context.

No full transcript replay should be necessary.

---

# 105. Example Safe AI Modification

Agent:

> Delete duplicate files.

StorageOS responds internally:

```text proposal:
DELETE 27 duplicate files

estimated reclaim:
14.8 GB

source snapshot:
184

evidence:
exact content hashes

risk:
low

rollback:
available
```

User approves.

Then:

```text snapshot
→ transaction
→ execution
→ verification
→ incremental index update
```

---

# 106. Developer Mode

For software repositories, expose:

```text repository
→ package
→ module
→ file
→ class
→ function
→ dependency
→ test
```

Queries:

```text Where is the implementation of X?
What depends on Y?
Which files are related to this bug?
What code introduced this behavior?
```

The same graph/evidence infrastructure should answer these.

---

# 107. Research Mode

Allow indexing of:

```text papers
notes
PDFs
web archives
videos
datasets
code
experiments
```

Provide:

```text literature graph
citation-like relationships
concept graph
evidence map
timeline
```

Research Mode should be built from the same underlying primitives.

---

# 108. AI-Ready Folder Manifest

Every indexed information space may optionally contain:

```text .ai/
```

with:

```text manifest.json
tree metadata
logical IDs
address map
ontology
summary metadata
index metadata
version information
```

The manifest must contain pointers/references, not unnecessary duplication of source data.

Example:

```json
{
  "protocol": "UINP",
  "space_id": "...",
  "root_address": "...",
  "representation_version": "...",
  "available_indexes": [
    "metadata",
    "fts",
    "graph",
    "hierarchy"
  ]
}
```

---

# 109. Interoperability

The protocol should be serializable.

Potential formats:

```text JSON
JSONL
MessagePack
Parquet for large analytical exports
```

The canonical runtime representation should not depend on a single export format.

---

# 110. Import / Export

Support exporting:

```text metadata
knowledge graph
addresses
provenance
snapshots
benchmark results
```

A full source copy is not necessary.

---

# 111. Observability

Every retrieval should be diagnosable.

Log:

```text query
planner
candidate operations
cost estimates
chosen actions
nodes visited
evidence selected
tokens
latency
outcome
```

The default UI can summarize this without exposing overwhelming detail.

---

# 112. Research Reproducibility

Every benchmark result must record:

```text corpus version
source hashes
StorageOS version
index version
algorithm
configuration
model
model version
embedding version
hardware
token budget
retrieval budget
random seeds where applicable
```

---

# 113. Acceptance Criteria — Core

The project is not considered functionally complete until:

1. A directory/drive can be indexed without modifying its contents.
2. Files have stable logical IDs.
3. Changes are detected incrementally.
4. Derived state can be rebuilt.
5. FTS search works without an LLM.
6. The knowledge graph works without a graph database.
7. Hierarchical navigation works.
8. Provenance exists for derived evidence.
9. Semantic addresses resolve correctly.
10. AI can navigate via high-level tools.
11. AI cannot perform destructive actions without the transaction layer.
12. Retrieval supports budget constraints.
13. Retrieval can stop adaptively.
14. Context can be compiled under a token budget.
15. Persistent task state can reconstruct prior context.
16. Locality statistics are recorded.
17. Frequently accessed information can be promoted.
18. Cold information remains searchable.
19. benchmark infrastructure compares algorithms.
20. all benchmark measurements are reproducible.

---

# 114. Acceptance Criteria — Efficiency

The system must demonstrate that:

### Representation

It can avoid expensive processing for data that does not justify it.

### Retrieval

It can achieve relevant evidence using multiple retrieval strategies.

### Context

It can produce a smaller context than raw retrieval for benchmark queries without unacceptable quality degradation.

### Adaptation

Repeated workloads can reduce retrieval cost over time.

### Incremental updates

Changing a small portion of a dataset should not require rebuilding unrelated derived state.

---

# 115. Acceptance Criteria — Safety

Required:

```text source files survive indexing
source files survive failed indexing
AI proposals are auditable
destructive actions require authorization
operations are rollback-capable where practical
stale knowledge is detectable
provenance is not silently fabricated
```

---

# 116. Acceptance Criteria — Scale

The API/data model must be independent of corpus size.

Test at multiple synthetic scales:

```text 10K objects
100K objects
1M objects
10M logical objects
```

where hardware permits.

At large scale, the reference implementation may use partitioning rather than new architectural semantics.

---

# 117. Phased Build Plan

## Phase 0 — Foundation

Implement:

```text core models
SQLite
source identity
versions
provenance
filesystem adapter
basic CLI
```

## Phase 1 — Storage Intelligence

Implement:

```text disk overview
file categorization
duplicates
large files
history
watcher
cleanup proposals
```

## Phase 2 — Universal Parsing

Implement:

```text PDF
DOCX
PPTX
XLSX
CSV
MD/TXT
code
image
audio
video
archives
```

using a common evidence model.

## Phase 3 — Knowledge Representation

Implement:

```text hierarchy
ontology
graph
entities
relationships
evidence
summaries
communities
```

## Phase 4 — Search and Retrieval

Implement:

```text FTS
graph search
tree search
vector interface
hybrid retrieval
reranking
```

## Phase 5 — Algorithm Laboratory

Implement:

```text Dijkstra
A*
Beam
Bandits
PCST
Set Cover
CARVE
```

## Phase 6 — Context System

Implement:

```text task state
memory
delta context
context compiler
context virtual memory
```

## Phase 7 — Adaptive System

Implement:

```text locality
route learning
adaptive materialization
hot/warm/cold
prefetch
```

## Phase 8 — Semantic Addressing

Implement:

```text canonical IDs
logical addresses
human aliases
fuzzy correction
version resolution
```

## Phase 9 — AI Operations

Implement:

```text propose
validate
preview
snapshot
transaction
rollback
```

## Phase 10 — Research Benchmark

Implement:

```text baselines
datasets
metrics
ablation
cost reports
reproducibility
```

## Phase 11 — Dashboard

Implement:

```text storage
knowledge
graph
retrieval diagnostics
context
locality
operations
benchmarks
```

---

# 118. Definition of Done for Every Phase

Every phase must include:

```text implementation
unit tests
integration tests
failure tests
documentation
CLI usage
API exposure where applicable
benchmark instrumentation
```

No “working” feature without tests.

---

# 119. OpenCode Build Instructions

OpenCode should be instructed to:

1. Build the repository incrementally.
2. Keep the application runnable after every major phase.
3. Run tests after each implementation segment.
4. Diagnose and fix failures rather than bypassing tests.
5. Never remove requirements silently.
6. Never simplify by deleting major capabilities.
7. Reduce complexity through shared abstractions.
8. Use optional dependencies for expensive functionality.
9. Preserve source immutability.
10. Implement benchmark harnesses alongside algorithms.
11. Record assumptions in architecture documentation.
12. Prefer deterministic implementations before LLM-dependent implementations.
13. Avoid introducing infrastructure that the reference implementation does not require.
14. Make experimental algorithms independently switchable.
15. Keep all advanced modules replaceable.

---

# 120. Anti-Requirements

The system must NOT become:

```text
just a vector database
just GraphRAG
just a file explorer
just a cleanup utility
just a chatbot
just a memory database
just a semantic search engine
just a dashboard
```

It is the combination of:

```text
immutable information source
+
optimized representation
+
persistent knowledge space
+
adaptive navigation
+
evidence retrieval
+
bounded context
+
safe action layer
```

---

# 121. Architecture Simplicity Rule

Before introducing a new dependency/system, ask:

```text Can SQLite do this?
Can the existing core do this?
Can this be an adapter?
Can this be lazy?
Can this be derived?
Can this share an existing primitive?
```

Prefer:

```text reuse > duplication
interfaces > coupling
derived views > duplicated truth
lazy > eager
local > distributed
configurable > hard-coded
measured > assumed
```

---

# 122. Long-Term Extension Path

Future implementations may add:

```text distributed indexing
remote object stores
cloud repositories
database adapters
federated information spaces
multi-user permissions
multi-agent shared memory
hardware-aware routing
GPU retrieval
specialized vector engines
distributed graph engines
```

None should require changing the core logical protocol.

---

# 123. Central Protocol Abstraction

The long-term system should expose:

```text Universal Information Navigation Protocol
```

Conceptually:

```text resolve(object/address)
navigate(from, goal, budget)
inspect(object)
expand(object, level)
retrieve(query, budget)
evidence(object)
remember(state)
context(task, budget)
propose(object, operation)
```

The protocol describes **what the AI can ask the information space**, not where the information is stored.

---

# 124. Final Research Hypothesis

StorageOS should ultimately test:

> **A digital information space can be made substantially more efficient for AI not primarily by increasing model context or continuously adding larger embeddings, but by compiling the source into a multi-resolution, provenance-aware information representation whose physical and semantic organization adapts to workload, and by treating retrieval as budget-constrained navigation toward sufficient evidence.**

The strongest version adds:

> **A bounded context compiler can prevent persistent AI tasks from depending on ever-growing active context windows by externalizing task state and reconstructing only the information required for the current reasoning step.**

The project should report honestly whether the experiments support or reject these hypotheses.

---

# 125. Ultimate Product Model

```text
                     STORAGEOS
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
   SOURCE TRUTH     KNOWLEDGE SPACE   AI WORKING SPACE
        │                │                 │
   immutable          adaptive          bounded
   versioned          indexed           compiled
   auditable          addressable       persistent
        │                │                 │
        └────────────────┼─────────────────┘
                         │
                  UNIVERSAL PROTOCOL
                         │
                         ▼
                 COST-AWARE NAVIGATOR
                         │
                         ▼
                    MINIMUM SUFFICIENT
                         EVIDENCE
                         │
                         ▼
                  MINIMUM SUFFICIENT
                      CONTEXT
                         │
                         ▼
                         AI
                         │
                 ┌───────┴────────┐
                 ▼                ▼
             knowledge         actions
               update          proposals
                 │                │
                 └───────┬────────┘
                         ▼
                    LEARNING LOOP
                         │
                         ▼
               CHEAPER FUTURE ACCESS
```

---

# 126. Product Mantra

> **Keep the source intact.  
> Compile the information intelligently.  
> Store only useful derived knowledge.  
> Navigate instead of dumping.  
> Retrieve evidence instead of chunks.  
> Treat context as a cache.  
> Learn locality from use.  
> Make hot information cheaper, never cold information inaccessible.  
> Measure every token, byte, CPU cycle and I/O operation.  
> Maximize capability without multiplying architecture.**

---

# 127. Final Success Condition

StorageOS succeeds as a research prototype if it can demonstrate, on controlled workloads, that:

1. arbitrary heterogeneous information can be represented through a unified evidence model;
2. source data can remain untouched while derived intelligence evolves independently;
3. representation decisions can be made before expensive indexing;
4. multiple retrieval algorithms can operate over the same substrate;
5. the planner can select different algorithms according to query and cost;
6. adaptive locality can make repeated information access cheaper;
7. evidence selection can reduce redundancy and token consumption;
8. the context compiler can preserve task continuity under bounded context;
9. provenance can be maintained from answer → evidence → source;
10. incremental changes can propagate without unnecessary full rebuilds;
11. the entire system can run locally without requiring a large infrastructure stack;
12. experimental evidence—not architectural assumptions—determines whether the proposed methods actually outperform simpler baselines.

The ultimate goal is not to create the biggest index.

It is to create the **smallest, fastest, most useful representation capable of reliably navigating the entire information space.**