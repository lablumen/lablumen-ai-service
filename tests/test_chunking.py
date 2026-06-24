from src.chunking import chunk_text


def test_chunk_text_splits_on_size():
    text = "\n\n".join(f"Paragraph number {i} with some content." for i in range(50))
    chunks = chunk_text(text, max_chars=200)
    assert len(chunks) > 1
    assert all(len(c) <= 250 for c in chunks)  # allow small overshoot from joining


def test_chunk_text_empty():
    assert chunk_text("") == []
