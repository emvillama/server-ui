"""
Splits raw text into chunks for embedding. Aims for a target chunk size
but adjusts the cut point to land on a sentence boundary where possible,
so chunks don't get cut off mid-sentence. Falls back to the nearest word
boundary if no sentence boundary is found nearby, and only falls back to
a hard character cut if there's no space to find at all (e.g. one giant
unbroken token).
"""

import re

# Matches sentence-ending punctuation followed by whitespace -- the cut
# point lands right after this.
_SENTENCE_END = re.compile(r"[.!?]\s+")


def chunk_text(
    text: str, target_size: int = 500, max_search: int = 200
) -> list[str]:
    """
    Splits `text` into chunks of roughly `target_size` characters each,
    preferring to cut at a sentence boundary near that target rather than
    exactly at it.

    target_size: desired chunk length in characters.
    max_search:  how far past target_size to look for a sentence boundary
                 before falling back to a word-boundary cut instead.
    """
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        # If what's left is already shorter than the target, it's the
        # last chunk -- take all of it and stop.
        if text_len - start <= target_size:
            chunks.append(text[start:].strip())
            break

        # Look for a sentence boundary between target_size and
        # target_size + max_search, measured from `start`.
        search_start = start + target_size
        search_end = min(start + target_size + max_search, text_len)
        window = text[search_start:search_end]

        match = _SENTENCE_END.search(window)
        if match:
            # Cut right after the matched punctuation + whitespace.
            cut = search_start + match.end()
        else:
            # No sentence boundary found nearby. Fall back to the nearest
            # word boundary (last space) at or before search_start, so we
            # at least don't cut a word in half. Only fall back to a hard
            # character cut if there's no space to find at all.
            last_space = text.rfind(" ", start, search_start)
            cut = last_space + 1 if last_space != -1 else search_start

        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        start = cut

    return chunks