"""
Deterministic text chunking for the knowledge layer.

Pure functions only: no ORM, no AI provider, no randomness. The
same input always produces the same ordered list of non-empty
chunks.
"""


SECRET_MARKERS = (
    "OPENAI_API_KEY",
    "SECRET_KEY",
    "AWS_SECRET",
    "PASSWORD=",
    "PRIVATE KEY",
    "BEGIN RSA",
    "BEGIN OPENSSH",
)


def normalize_text(text):
    """
    Collapse all whitespace runs to single spaces and strip ends.

    Deterministic and idempotent.
    """

    if not isinstance(text, str):
        raise ValueError("text must be a string.")

    return " ".join(text.split())


def looks_like_secret(text):
    """
    Cheap guard so obvious credential material is never ingested as
    knowledge. Not a security boundary on its own - ingestion also
    restricts source types - but a clear safety net.
    """

    upper = (text or "").upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def chunk_text(text, *, chunk_size, overlap):
    """
    Split ``text`` into an ordered list of non-empty chunks.

    - operates on whitespace-normalized words
    - each chunk is <= ``chunk_size`` characters unless a single
      word is longer than ``chunk_size`` (that word is its own
      chunk)
    - consecutive chunks share up to ``overlap`` trailing
      characters of context
    - deterministic: identical input -> identical output
    - raises ValueError on empty / whitespace-only input or invalid
      sizing
    """

    if not isinstance(chunk_size, int) or isinstance(
        chunk_size, bool
    ) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")

    if not isinstance(overlap, int) or isinstance(
        overlap, bool
    ) or overlap < 0:
        raise ValueError("overlap must be a non-negative integer.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    normalized = normalize_text(text)

    if not normalized:
        raise ValueError("Cannot chunk empty content.")

    words = normalized.split(" ")

    chunks = []
    current = []
    current_len = 0

    def _flush():
        if current:
            chunks.append(" ".join(current))

    for word in words:
        addition = len(word) if not current else len(word) + 1

        if current and current_len + addition > chunk_size:
            _flush()

            # Carry trailing words as overlap context.
            carry = []
            carry_len = 0
            for prev in reversed(current):
                prev_add = (
                    len(prev) if not carry else len(prev) + 1
                )
                if carry_len + prev_add > overlap:
                    break
                carry.insert(0, prev)
                carry_len += prev_add

            current = carry
            current_len = carry_len
            addition = len(word) if not current else len(word) + 1

        current.append(word)
        current_len += addition

    _flush()

    return chunks
