def chunk_text(text: str, max_words: int = 220, overlap: int = 40) -> list[str]:
    """Sliding word window. Overlap keeps a sentence that straddles a boundary
    retrievable from at least one chunk."""
    if overlap >= max_words:
        raise ValueError("overlap must be smaller than max_words")
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks
