"""
Deterministic lexical ranking for knowledge retrieval.

Pure functions only: no ORM, no AI provider, no embeddings, no
randomness. Ranking is a token-overlap score over chunk content:

    score = (distinct query terms present in the chunk)
          + (total query-term occurrences / chunk token count)

The integer part (distinct-term coverage) dominates; the fractional
part is a stable tie-breaker favouring denser matches. Remaining
ties break by (document_id, chunk_index) so output is fully
deterministic.

This is intentionally embedding-free: the current deployment is
SQLite with no pgvector. The interface returns real stored chunks
as evidence, so a vector ranker can replace `rank_chunks` later
without changing callers.
"""

import re


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _TOKEN_RE.findall((text or "").lower())


def score_chunk(*, query_tokens, content):
    chunk_tokens = tokenize(content)
    if not chunk_tokens:
        return 0.0

    distinct_query = set(query_tokens)
    if not distinct_query:
        return 0.0

    occurrences = 0
    matched_terms = 0

    for term in distinct_query:
        count = chunk_tokens.count(term)
        if count:
            matched_terms += 1
            occurrences += count

    if matched_terms == 0:
        return 0.0

    return matched_terms + (occurrences / len(chunk_tokens))


def rank_chunks(*, query, chunks, limit):
    """
    Rank ``chunks`` (list of dicts with at least ``content``,
    ``document_id``, ``chunk_index``) against ``query``.

    Returns the top ``limit`` chunks, each with a ``score`` key
    added, best first. Chunks that match nothing are dropped.
    """

    query_tokens = tokenize(query)

    scored = []
    for chunk in chunks:
        score = score_chunk(
            query_tokens=query_tokens,
            content=chunk.get("content", ""),
        )
        if score > 0:
            scored.append((score, chunk))

    scored.sort(
        key=lambda pair: (
            -pair[0],
            pair[1].get("document_id", 0),
            pair[1].get("chunk_index", 0),
        ),
    )

    results = []
    for score, chunk in scored[: max(0, int(limit))]:
        enriched = dict(chunk)
        enriched["score"] = round(score, 6)
        results.append(enriched)

    return results
