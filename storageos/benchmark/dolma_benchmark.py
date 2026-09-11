"""Dolma benchmark: 20 questions + FTS retrieval + LLM evaluation with gpt-oss:20b-cloud."""
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(r"C:\Users\Anand\Downloads\dolma-v1_6-slice\dolma.db")
RESULTS_DIR = Path(r"C:\Users\Anand\Desktop\Storage OS\results")

QUESTIONS = [
    # Heading-aligned (answerable from single source)
    {"id": "D01", "text": "What country does the ambassador Anne Anderson represent?",
     "bucket": "heading-aligned", "source_filter": "common-crawl"},
    {"id": "D02", "text": "What is the name of the 8-year-old boy who rescued people from a fire?",
     "bucket": "heading-aligned", "source_filter": "common-crawl"},
    {"id": "D03", "text": "What car model was Maserati's breakthrough vehicle?",
     "bucket": "heading-aligned", "source_filter": "common-crawl"},
    {"id": "D04", "text": "What happened in Toledo Ohio regarding water supply in August 2014?",
     "bucket": "heading-aligned", "source_filter": "common-crawl"},
    {"id": "D05", "text": "What is the capacity of LTO-8 tape storage?",
     "bucket": "heading-aligned", "source_filter": "c4"},
    {"id": "D06", "text": "What book did Gabrielle E Jackson write?",
     "bucket": "heading-aligned", "source_filter": "gutenberg"},
    {"id": "D07", "text": "Who is Leonard Brody and what is he recognized for?",
     "bucket": "heading-aligned", "source_filter": "common-crawl"},
    {"id": "D08", "text": "What is Parquest Capital and when was it created?",
     "bucket": "heading-aligned", "source_filter": "c4"},

    # Heading-misaligned (requires understanding across related content)
    {"id": "D09", "text": "Which authors in this corpus wrote about life in ancient Rome?",
     "bucket": "heading-misaligned"},
    {"id": "D10", "text": "What topics do the gutenberg books in this collection cover?",
     "bucket": "heading-misaligned"},
    {"id": "D11", "text": "How are c4 and common-crawl sources different in content style?",
     "bucket": "heading-misaligned"},
    {"id": "D12", "text": "What types of stories appear in the colonial days collection?",
     "bucket": "heading-misaligned"},

    # Cross-document (synthesis across multiple documents)
    {"id": "D13", "text": "What European countries are mentioned across news articles in this corpus?",
     "bucket": "cross-document"},
    {"id": "D14", "text": "What sports events are described across the web documents?",
     "bucket": "cross-document"},
    {"id": "D15", "text": "What technology products are mentioned in the c4 documents?",
     "bucket": "cross-document"},
    {"id": "D16", "text": "What historical periods are covered by the gutenberg books?",
     "bucket": "cross-document"},
    {"id": "D17", "text": "What are the common themes across the children's literature in this corpus?",
     "bucket": "cross-document"},
    {"id": "D18", "text": "What environmental topics appear across the web crawl documents?",
     "bucket": "cross-document"},
    {"id": "D19", "text": "What biographical information is available about authors in this corpus?",
     "bucket": "cross-document"},
    {"id": "D20", "text": "What international news stories are covered in the common-crawl data?",
     "bucket": "cross-document"},
]

RETRIEVAL_LIMIT = 10
LLM_MODEL = "gpt-oss:20b-cloud"


STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "of", "for", "to", "and",
    "or", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "this", "that", "these", "those", "what", "which", "who",
    "whom", "whose", "where", "when", "why", "how", "not", "no", "nor",
    "so", "but", "if", "then", "than", "too", "very", "just", "about",
    "above", "after", "again", "all", "also", "any", "because", "before",
    "between", "both", "each", "few", "more", "most", "other", "some",
    "such", "into", "over", "own", "same", "through", "during", "out",
    "up", "down", "from", "with", "at", "by", "as", "its", "their",
    "they", "them", "he", "she", "we", "you", "me", "my", "your", "his",
    "her", "our", "us",
}


def run_fts_search(query, limit=RETRIEVAL_LIMIT):
    """Run FTS search on the Dolma DB."""
    conn = sqlite3.connect(str(DB_PATH))
    import re
    tokens = re.findall(r"\w+", query.lower())
    # Filter stopwords
    meaningful = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    if not meaningful:
        meaningful = tokens[:5]  # fallback: use first 5 tokens
    safe_query = " OR ".join(f'"{t}"' for t in meaningful)

    t0 = time.time()
    rows = conn.execute(
        """SELECT passage_id, text FROM passages_fts
           WHERE passages_fts MATCH ?
           ORDER BY rank
           LIMIT ?""",
        (safe_query, limit * 3)  # overfetch, then deduplicate
    ).fetchall()
    latency_ms = (time.time() - t0) * 1000

    # Deduplicate by passage_id
    seen = set()
    unique_rows = []
    for row in rows:
        if row[0] not in seen:
            seen.add(row[0])
            unique_rows.append(row)
    rows = unique_rows[:limit]

    # Get source info
    results = []
    for row in rows:
        passage_id, text = row
        res = conn.execute(
            """SELECT p.resource_id, r.absolute_path, p.start_offset, p.end_offset
               FROM passages p
               JOIN resources r ON r.resource_id = p.resource_id
               WHERE p.passage_id = ?""",
            (passage_id,)
        ).fetchone()
        if res:
            resource_id, source_path, start_off, end_off = res
        else:
            resource_id, source_path, start_off, end_off = "unknown", "unknown", 0, 0
        results.append({
            "passage_id": passage_id,
            "text": text[:500],
            "full_text_len": len(text),
            "source_path": source_path,
            "start_offset": start_off,
            "end_offset": end_off,
        })

    conn.close()
    return results, latency_ms


def call_llm(prompt, model=LLM_MODEL):
    """Call Ollama API for LLM evaluation."""
    import urllib.request
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512}
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    latency_ms = (time.time() - t0) * 1000
    return result.get("response", "").strip(), latency_ms


def run_benchmark():
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}
    total_tokens_in = 0
    total_tokens_out = 0

    for q in QUESTIONS:
        qid = q["id"]
        print(f"\n{'='*60}")
        print(f"[{qid}] {q['text']}")
        print(f"  Bucket: {q['bucket']}")

        # Step 1: FTS retrieval
        print(f"  Retrieving...", end=" ", flush=True)
        passages, retrieval_ms = run_fts_search(q["text"])
        print(f"{len(passages)} passages in {retrieval_ms:.1f}ms")

        # Build context from passages
        context = "\n\n---\n\n".join(
            f"[Source: {p['source_path']}]\n{p['text']}"
            for p in passages
        )

        # Step 2: LLM answer generation
        prompt = f"""You are answering questions based on retrieved documents from a large corpus.

Question: {q['text']}

Retrieved passages:
{context}

Answer the question based ONLY on the retrieved passages. Be specific and cite sources. If the passages don't contain enough information, say so."""

        print(f"  Calling LLM...", end=" ", flush=True)
        answer, llm_ms = call_llm(prompt)
        print(f"done ({llm_ms:.0f}ms)")
        print(f"  Answer: {answer[:200]}...")

        # Step 3: LLM relevance judgment
        judge_prompt = """Rate the relevance of this answer to the question on a scale of 1-5:
1 = Completely wrong/unrelated
2 = Partially related but mostly incorrect
3 = Partially correct
4 = Mostly correct and relevant
5 = Fully correct and well-supported

Question: {question}

Answer: {answer}

Rating (just the number):"""

        rating, judge_ms = call_llm(judge_prompt.format(question=q["text"], answer=answer))

        results[qid] = {
            "question": q["text"],
            "bucket": q["bucket"],
            "retrieval_ms": retrieval_ms,
            "passages_found": len(passages),
            "passages": passages,
            "llm_latency_ms": llm_ms,
            "answer": answer,
            "relevance_rating": rating.strip(),
            "judge_latency_ms": judge_ms,
        }

        print(f"  Relevance: {rating.strip()}/5")

    # Save results
    out_path = RESULTS_DIR / "dolma_benchmark_results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved: {out_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"BENCHMARK SUMMARY")
    print(f"{'='*60}")
    ratings = [int(r["relevance_rating"][0]) for r in results.values() if r["relevance_rating"] and r["relevance_rating"][0].isdigit()]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    avg_retrieval = sum(r["retrieval_ms"] for r in results.values()) / len(results)
    avg_llm = sum(r["llm_latency_ms"] for r in results.values()) / len(results)
    print(f"Questions: {len(results)}")
    print(f"Avg relevance: {avg_rating:.2f}/5")
    print(f"Avg retrieval: {avg_retrieval:.1f}ms")
    print(f"Avg LLM latency: {avg_llm:.0f}ms")

    # By bucket
    for bucket in ["heading-aligned", "heading-misaligned", "cross-document"]:
        bucket_results = {k: v for k, v in results.items() if v["bucket"] == bucket}
        if bucket_results:
            bucket_ratings = [int(r["relevance_rating"][0]) for r in bucket_results.values() if r["relevance_rating"] and r["relevance_rating"][0].isdigit()]
            if bucket_ratings:
                print(f"  {bucket}: {sum(bucket_ratings)/len(bucket_ratings):.2f}/5 ({len(bucket_results)} questions)")


if __name__ == "__main__":
    run_benchmark()
