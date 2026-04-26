#!/usr/bin/env python3
"""
RAG Search Quality Evaluation Harness

Measures retrieval quality (MRR, Hit@K) against a golden query dataset.

Usage:
    python scripts/eval_search.py
    python scripts/eval_search.py --url http://localhost:8000
    python scripts/eval_search.py --category thematic --verbose
    python scripts/eval_search.py --output results.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

GOLDEN_QUERIES_PATH = Path(__file__).parent.parent / "data" / "golden_queries.json"
DEFAULT_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30
TOP_K = 10


def load_golden_queries(path: Path, category_filter: str | None = None) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        queries = json.load(f)
    if category_filter:
        queries = [q for q in queries if q.get("category") == category_filter]
    return queries


def call_search_api(base_url: str, query: str, num_results: int = TOP_K) -> list[dict]:
    """Call /api/search and collect verse results from the NDJSON stream."""
    verses = []
    try:
        resp = requests.post(
            f"{base_url}/api/search",
            json={"query": query, "translations": ["NIV"], "num_results": num_results},
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            if t == "verse":
                verses.append(obj)
            elif t in ("complete", "error", "done"):
                break
    except requests.exceptions.ConnectionError:
        raise
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] Query timed out after {REQUEST_TIMEOUT}s")
    except requests.exceptions.HTTPError as e:
        print(f"  [HTTP ERROR] {e}")
    return verses


def verse_matches(result: dict, expected: dict) -> bool:
    """Check if a search result matches an expected verse."""
    book_match = result.get("book", "").lower() == expected["book"].lower()
    chapter_match = int(result.get("chapter", -1)) == expected["chapter"]
    verse_match = int(result.get("verse", -1)) == expected["verse"]
    return book_match and chapter_match and verse_match


def evaluate_query(results: list[dict], expected_verses: list[dict]) -> dict:
    """Compute hit@1, hit@5, hit@10, and reciprocal rank for one query."""
    rr = 0.0
    hit1 = hit5 = hit10 = False

    for rank, result in enumerate(results[:TOP_K], start=1):
        matched = any(verse_matches(result, ev) for ev in expected_verses)
        if matched:
            if rr == 0.0:
                rr = 1.0 / rank
            if rank == 1:
                hit1 = True
            if rank <= 5:
                hit5 = True
            if rank <= 10:
                hit10 = True

    return {"hit@1": hit1, "hit@5": hit5, "hit@10": hit10, "rr": rr}


def aggregate(metrics: list[dict]) -> dict:
    n = len(metrics)
    if n == 0:
        return {"mrr": 0.0, "hit@1": 0.0, "hit@5": 0.0, "hit@10": 0.0, "n": 0}
    return {
        "mrr": sum(m["rr"] for m in metrics) / n,
        "hit@1": sum(m["hit@1"] for m in metrics) / n,
        "hit@5": sum(m["hit@5"] for m in metrics) / n,
        "hit@10": sum(m["hit@10"] for m in metrics) / n,
        "n": n,
    }


def fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def print_aggregate(label: str, agg: dict, indent: int = 0) -> None:
    pad = " " * indent
    print(
        f"{pad}{label:<22}  MRR={agg['mrr']:.3f}  "
        f"Hit@1={fmt_pct(agg['hit@1'])}  "
        f"Hit@5={fmt_pct(agg['hit@5'])}  "
        f"Hit@10={fmt_pct(agg['hit@10'])}  "
        f"(n={agg['n']})"
    )


def run_evaluation(
    base_url: str,
    queries: list[dict],
    verbose: bool = False,
) -> list[dict[str, Any]]:
    results_log: list[dict[str, Any]] = []
    total = len(queries)

    for i, q in enumerate(queries, start=1):
        qid = q["id"]
        query_text = q["query"]
        expected = q["expected_verses"]

        prefix = f"[{i}/{total}] {query_text[:55]:<55}"
        print(prefix, end="", flush=True)

        t0 = time.time()
        try:
            api_results = call_search_api(base_url, query_text)
        except requests.exceptions.ConnectionError:
            print(f"  [CONNECTION ERROR] Is the server running at {base_url}?")
            sys.exit(1)
        elapsed = time.time() - t0

        metrics = evaluate_query(api_results, expected)

        hit_label = (
            "Hit@1 ✓" if metrics["hit@1"]
            else "Hit@5 ✓" if metrics["hit@5"]
            else "Hit@10 ✓" if metrics["hit@10"]
            else "MISS"
        )
        rr_label = f"RR={metrics['rr']:.2f}" if metrics["rr"] > 0 else "RR=0"
        print(f"  {hit_label}  {rr_label}  ({elapsed:.1f}s)")

        if verbose:
            for rank, r in enumerate(api_results[:5], 1):
                book = r.get("book", "?")
                ch = r.get("chapter", "?")
                vs = r.get("verse", "?")
                is_hit = any(verse_matches(r, ev) for ev in expected)
                marker = "★" if is_hit else " "
                print(f"    {marker} {rank}. {book} {ch}:{vs}")

        results_log.append({
            "id": qid,
            "query": query_text,
            "language": q.get("language"),
            "category": q.get("category"),
            "metrics": metrics,
            "elapsed_s": round(elapsed, 2),
            "top_results": [
                {"book": r.get("book"), "chapter": r.get("chapter"), "verse": r.get("verse")}
                for r in api_results[:10]
            ],
        })

    return results_log


def main() -> None:
    parser = argparse.ArgumentParser(description="Bible RAG search quality evaluation")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--golden", default=str(GOLDEN_QUERIES_PATH), help="Golden queries JSON path")
    parser.add_argument("--output", help="Save full results to JSON file")
    parser.add_argument("--category", help="Filter by category (direct_reference|thematic|person|cross_lingual)")
    parser.add_argument("--language", choices=["en", "ko"], help="Filter by language")
    parser.add_argument("--verbose", action="store_true", help="Show top-5 results per query")
    args = parser.parse_args()

    queries = load_golden_queries(Path(args.golden), args.category)
    if args.language:
        queries = [q for q in queries if q.get("language") == args.language]

    if not queries:
        print("No queries matched the given filters.")
        sys.exit(1)

    print("=" * 70)
    print("Bible RAG — Search Quality Evaluation")
    print("=" * 70)
    print(f"Server : {args.url}")
    print(f"Queries: {len(queries)}")
    if args.category:
        print(f"Filter : category={args.category}")
    if args.language:
        print(f"Filter : language={args.language}")
    print("-" * 70)

    results_log = run_evaluation(args.url, queries, verbose=args.verbose)

    all_metrics = [r["metrics"] for r in results_log]
    en_metrics = [r["metrics"] for r in results_log if r.get("language") == "en"]
    ko_metrics = [r["metrics"] for r in results_log if r.get("language") == "ko"]

    categories: dict[str, list] = {}
    for r in results_log:
        cat = r.get("category", "unknown")
        categories.setdefault(cat, []).append(r["metrics"])

    print("\n" + "=" * 70)
    print("Results Summary")
    print("=" * 70)
    print_aggregate("Overall", aggregate(all_metrics))

    print("\nBy Language:")
    if en_metrics:
        print_aggregate("English", aggregate(en_metrics), indent=2)
    if ko_metrics:
        print_aggregate("Korean", aggregate(ko_metrics), indent=2)

    print("\nBy Category:")
    for cat, mlist in sorted(categories.items()):
        print_aggregate(cat, aggregate(mlist), indent=2)

    avg_elapsed = sum(r["elapsed_s"] for r in results_log) / len(results_log)
    print(f"\nAvg latency per query: {avg_elapsed:.1f}s")

    if args.output:
        out = {
            "url": args.url,
            "total_queries": len(results_log),
            "aggregate": aggregate(all_metrics),
            "by_language": {
                "en": aggregate(en_metrics),
                "ko": aggregate(ko_metrics),
            },
            "by_category": {cat: aggregate(m) for cat, m in categories.items()},
            "queries": results_log,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\nFull results saved to: {args.output}")


if __name__ == "__main__":
    main()