from backend.services.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "This is a short sentence."
    assert chunk_text(text, target_size=500) == [text]


def test_long_text_splits_into_multiple_chunks():
    sentence = "The mitochondria is the powerhouse of the cell. "
    text = sentence * 20
    result = chunk_text(text, target_size=500, max_search=200)
    assert len(result) > 1


def test_chunks_end_on_sentence_boundaries():
    sentence = "The mitochondria is the powerhouse of the cell. "
    text = sentence * 20
    result = chunk_text(text, target_size=500, max_search=200)
    for chunk in result[:-1]:
        assert chunk.rstrip()[-1] in ".!?"


def test_fallback_never_cuts_a_word_in_half():
    # No punctuation at all, forces the word-boundary fallback path.
    text = "word " * 300
    result = chunk_text(text, target_size=500, max_search=200)
    assert len(result) > 1
    for chunk in result:
        for token in chunk.split():
            assert token == "word"


def test_reassembled_chunks_cover_original_content():
    sentence = "The mitochondria is the powerhouse of the cell. "
    text = (sentence * 20).strip()
    result = chunk_text(text, target_size=500, max_search=200)
    rejoined = " ".join(result)
    assert rejoined.count("mitochondria") == text.count("mitochondria")