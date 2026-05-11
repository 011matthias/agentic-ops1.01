# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.30",
#     "numpy>=1.26",
#     "pandas>=2.2",
#     "rapidfuzz>=3.6",
# ]
# ///
"""
Product Matching MVP, skeleton.

Runs the full ingest -> normalize -> dedupe -> embed -> search pipeline end-to-end
on a CSV of products. Designed to be obvious, not clever. Adapt the normalize
and dedupe functions to your supplier feeds; keep the embed and search loop intact.

Usage:
    export OPENAI_API_KEY=sk-...
    uv run product-matching-mvp-skeleton.py path/to/products.csv "alternatives to Bosch GSB 18V drill"

Expected CSV columns (rename in NORMALIZE_RENAMES below if yours differ):
    sku, brand, title, description, category, specs (free-text or JSON-ish)

Output:
    Top-K matches with confidence scores. Confidence is cosine similarity rescaled to 0-1.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from openai import OpenAI
from rapidfuzz import fuzz

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5
CONFIDENCE_HIGH = 0.85   # trust it
CONFIDENCE_MID = 0.65    # double-check

# Map your supplier-specific column names to canonical ones here.
NORMALIZE_RENAMES = {
    # "Article No.": "sku",
    # "Brand Name": "brand",
}


@dataclass
class Product:
    row_id: int
    sku: str
    brand: str
    category: str
    title: str
    composed: str  # the string we embed
    spec_hash: str


def normalize_row(row: pd.Series) -> Product:
    """Lowercase, strip, parse the composed embedding string. Adapt freely."""
    sku = str(row.get("sku", "")).strip().lower()
    brand = str(row.get("brand", "")).strip().lower()
    category = str(row.get("category", "")).strip().lower()
    title = str(row.get("title", "")).strip()
    specs_raw = str(row.get("specs", ""))

    # Normalize: collapse whitespace, strip punctuation that adds noise.
    title_norm = re.sub(r"\s+", " ", title.lower()).strip()
    specs_norm = re.sub(r"\s+", " ", specs_raw.lower()).strip()

    # Composed string for embedding. Brand first so it's heavily weighted in similarity.
    composed = f"{brand} | {title_norm} | {specs_norm}"

    # Deterministic spec hash for dedup signal.
    spec_hash = hashlib.sha1(specs_norm.encode("utf-8")).hexdigest()[:12]

    return Product(
        row_id=int(row.name),
        sku=sku,
        brand=brand,
        category=category,
        title=title_norm,
        composed=composed,
        spec_hash=spec_hash,
    )


def flag_missing(products: list[Product]) -> tuple[list[Product], list[Product]]:
    """Split into (clean, triage). Triage are not dropped, just flagged."""
    clean, triage = [], []
    for p in products:
        if not p.brand or not p.title:
            triage.append(p)
        else:
            clean.append(p)
    return clean, triage


def dedupe(products: list[Product]) -> dict[int, list[int]]:
    """
    Return clusters: canonical_row_id -> [duplicate_row_ids].
    Match rule: same brand AND (matching spec hash OR fuzzy SKU prefix OR fuzzy title >= 90).
    Conservative on purpose; better to under-merge than over-merge.
    """
    clusters: dict[int, list[int]] = {}
    assigned: set[int] = set()

    for i, a in enumerate(products):
        if a.row_id in assigned:
            continue
        clusters[a.row_id] = []
        assigned.add(a.row_id)
        for b in products[i + 1:]:
            if b.row_id in assigned:
                continue
            if a.brand != b.brand:
                continue
            same_spec_hash = a.spec_hash == b.spec_hash
            sku_match = a.sku and b.sku and fuzz.partial_ratio(a.sku, b.sku) >= 95
            title_match = fuzz.token_set_ratio(a.title, b.title) >= 90
            if same_spec_hash or sku_match or title_match:
                clusters[a.row_id].append(b.row_id)
                assigned.add(b.row_id)
    return clusters


def embed_batch(client: OpenAI, texts: list[str]) -> np.ndarray:
    """Batch embed. text-embedding-3-small is cheap, batch sizes up to ~2048 work fine."""
    BATCH = 256
    out = []
    for start in range(0, len(texts), BATCH):
        chunk = texts[start:start + BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=chunk)
        out.extend([d.embedding for d in resp.data])
    return np.array(out, dtype=np.float32)


def cosine_similarity_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Both arrays should be L2-normalized for cosine = dot."""
    return query @ corpus.T


def normalize_l2(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def confidence_label(score: float) -> str:
    if score >= CONFIDENCE_HIGH:
        return "HIGH"
    if score >= CONFIDENCE_MID:
        return "MID"
    return "LOW"


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: product-matching-mvp-skeleton.py <products.csv> <query string>")
        sys.exit(1)

    csv_path = sys.argv[1]
    query = sys.argv[2]

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY in env.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # 1. Load
    df = pd.read_csv(csv_path)
    if NORMALIZE_RENAMES:
        df = df.rename(columns=NORMALIZE_RENAMES)

    # 2. Normalize
    products = [normalize_row(df.iloc[i]) for i in range(len(df))]

    # 3. Triage missing fields, do not drop
    clean, triage = flag_missing(products)
    print(f"Normalized: {len(products)} rows. Clean: {len(clean)}. Triage (missing brand/title): {len(triage)}.")
    if triage:
        print(f"  Triage row ids (first 10): {[p.row_id for p in triage[:10]]}")

    # 4. Dedupe (conservative)
    clusters = dedupe(clean)
    canonical = list(clusters.keys())
    print(f"Dedupe: {len(clean)} clean -> {len(canonical)} canonical products.")
    n_merged = sum(len(v) for v in clusters.values())
    if n_merged:
        print(f"  Merged {n_merged} duplicate rows into {sum(1 for v in clusters.values() if v)} clusters.")

    # 5. Embed canonical products
    id_to_product = {p.row_id: p for p in clean}
    corpus_texts = [id_to_product[i].composed for i in canonical]
    print(f"Embedding {len(corpus_texts)} canonical products with {EMBED_MODEL}...")
    corpus_vectors = embed_batch(client, corpus_texts)
    corpus_vectors = normalize_l2(corpus_vectors)

    # 6. Embed query and search
    query_vector = embed_batch(client, [query])
    query_vector = normalize_l2(query_vector)

    scores = cosine_similarity_matrix(query_vector, corpus_vectors)[0]
    top_idx = np.argsort(-scores)[:TOP_K]

    # 7. Output with confidence
    print(f"\nQuery: {query!r}\n")
    print(f"{'Rank':<5} {'Conf':<6} {'Score':<7} {'Brand':<15} {'Title'}")
    print("-" * 80)
    for rank, idx in enumerate(top_idx, start=1):
        row_id = canonical[idx]
        p = id_to_product[row_id]
        score = float(scores[idx])
        # Rescale cosine similarity (-1..1, in practice 0..1 for text-embedding-3-small) to confidence.
        confidence = max(0.0, min(1.0, score))
        label = confidence_label(confidence)
        title_short = (p.title[:55] + "...") if len(p.title) > 58 else p.title
        print(f"{rank:<5} {label:<6} {confidence:<7.3f} {p.brand[:14]:<15} {title_short}")

    print("\nDone. Tune EMBED_MODEL, CONFIDENCE thresholds, and the dedupe rules per your data.")


if __name__ == "__main__":
    main()
