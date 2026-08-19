"""Deterministic bonus utilities for the Lab 19 GraphRAG notebook.

The functions in this module deliberately have no database or LLM dependency,
so their core correctness can be tested locally before they are called by the
notebook's Neo4j and OpenAI integration cells.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence

import pandas as pd


_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "at", "by", "for", "from", "how", "in", "is",
    "of", "on", "or", "the", "to", "what", "which", "with",
}


def _tokens(text: object) -> list[str]:
    return _TOKEN_RE.findall(str(text or "").casefold())


def _token_hash(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")


def simhash64(text: object) -> int:
    """Return a deterministic 64-bit SimHash for a text document."""
    weights = [0] * 64
    for token in _tokens(text):
        digest = _token_hash(token)
        for bit in range(64):
            weights[bit] += 1 if digest & (1 << bit) else -1
    return sum((1 << bit) for bit, weight in enumerate(weights) if weight >= 0)


def find_near_duplicate_pairs(
    texts: Sequence[object],
    threshold: float = 0.92,
    bands: int = 8,
) -> list[dict[str, float | int]]:
    """Find high-similarity candidates with SimHash LSH, without all-pairs search.

    LSH emits only documents sharing at least one band. Every emitted pair is
    then verified using the full 64-bit Hamming similarity, which makes the
    returned audit records deterministic and safe to review before merging.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    if bands <= 0 or 64 % bands:
        raise ValueError("bands must be a positive divisor of 64")

    fingerprints = [simhash64(text) for text in texts]
    bits_per_band = 64 // bands
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    candidates: set[tuple[int, int]] = set()

    for index, fingerprint in enumerate(fingerprints):
        for band in range(bands):
            signature = (fingerprint >> (band * bits_per_band)) & ((1 << bits_per_band) - 1)
            key = (band, signature)
            for previous in buckets[key]:
                candidates.add((previous, index))
            buckets[key].append(index)

    pairs: list[dict[str, float | int]] = []
    for left, right in sorted(candidates):
        hamming_distance = (fingerprints[left] ^ fingerprints[right]).bit_count()
        similarity = 1.0 - hamming_distance / 64.0
        if similarity >= threshold:
            pairs.append(
                {
                    "left_index": left,
                    "right_index": right,
                    "similarity": round(similarity, 6),
                    "hamming_distance": hamming_distance,
                }
            )
    return pairs


def traversal_edge_limit(
    degree: int,
    requested_limit: int,
    supernode_degree: int = 100,
    supernode_edge_cap: int = 50,
) -> int:
    """Apply the traversal cap exactly at the documented super-node boundary."""
    if degree > supernode_degree:
        return min(int(requested_limit), int(supernode_edge_cap))
    return int(requested_limit)


def build_community_reports(
    edges: pd.DataFrame,
    membership: Mapping[object, int],
    max_edges_per_report: int = 50,
) -> pd.DataFrame:
    """Turn community edges into deterministic, provenance-preserving reports."""
    expected = {
        "source", "target", "source_name", "relation", "target_name",
        "source_chunk_id", "published_date", "evidence",
    }
    missing = expected.difference(edges.columns)
    if missing:
        raise ValueError(f"edges missing required columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    work = edges.copy()
    work["community_id"] = work["source"].map(membership)
    work = work[work["community_id"].notna()].copy()
    if work.empty:
        return pd.DataFrame(columns=["community_id", "edge_count", "report"])

    work["community_id"] = work["community_id"].astype(int)
    work["published_date"] = work["published_date"].fillna("unknown").astype(str)
    for community_id, group in work.groupby("community_id", sort=True):
        recent = group.sort_values("published_date", ascending=False).head(max_edges_per_report)
        members = sorted(set(recent.source_name.astype(str)) | set(recent.target_name.astype(str)))
        lines = [
            f"Community {community_id}: {len(members)} entities, {len(group)} graph edges.",
            f"Entities: {', '.join(members[:20])}",
        ]
        for edge in recent.itertuples(index=False):
            evidence = " ".join(str(edge.evidence or "").split())
            lines.append(
                f"{edge.source_name} -{edge.relation}-> {edge.target_name} "
                f"| date={edge.published_date} | chunk={edge.source_chunk_id}"
                + (f" | evidence={evidence}" if evidence else "")
            )
        rows.append({"community_id": int(community_id), "edge_count": int(len(group)), "report": "\n".join(lines)})
    return pd.DataFrame(rows)


def select_community_reports(
    query: str,
    reports: pd.DataFrame,
    limit: int = 3,
) -> pd.DataFrame:
    """Rank community reports by transparent lexical overlap for Global Search."""
    if reports.empty:
        return reports.copy()
    if "report" not in reports.columns:
        raise ValueError("reports must contain a report column")

    query_terms = set(_tokens(query)).difference(_STOPWORDS)
    ranked = reports.copy()
    ranked["score"] = ranked["report"].map(
        lambda report: len(query_terms.intersection(_tokens(report)))
    )
    return ranked.sort_values(["score", "edge_count", "community_id"], ascending=[False, False, True]).head(limit).reset_index(drop=True)
