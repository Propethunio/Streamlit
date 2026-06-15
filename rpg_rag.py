"""
RAG dla historii sesji RPG.

Zamiast wysyłać ostatnie N wiadomości do AI, wybieramy:
  - ostatnie RECENT_K wiadomości (świeży kontekst)
  - top RELEVANT_K wiadomości z dalszej historii wg podobieństwa semantycznego do bieżącej akcji gracza

Model: paraphrase-multilingual-MiniLM-L12-v2 — obsługuje język polski.
Embeddingi są przechowywane w SQLite jako BLOB (numpy float32 bytes).
"""

import numpy as np
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings

import rpg_database

_RPG_EMBED_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

RECENT_K = 4    # ostatnie N wiadomości zawsze dołączone
RELEVANT_K = 4  # top N wiadomości z dalszej historii (wg podobieństwa)


@st.cache_resource
def _get_rpg_embeddings():
    return HuggingFaceEmbeddings(
        model_name=_RPG_EMBED_MODEL_ID,
        model_kwargs={"device": "cpu", "trust_remote_code": True},
    )


def _embed(text):
    model = _get_rpg_embeddings()
    return np.array(model.embed_query(text), dtype=np.float32)


def _cosine_sim(a, b):
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 1e-10 else 0.0


def embed_and_store(message_id, text):
    """Oblicza embedding tekstu i zapisuje go w bazie danych."""
    vec = _embed(text)
    rpg_database.save_message_embedding(message_id, vec.tobytes())


def build_relevant_history(query):
    """
    Zwraca listę wiadomości {"role", "content"} posortowanych chronologicznie.
    Łączy ostatnie RECENT_K wiadomości z top RELEVANT_K semantycznie powiązanych
    ze starszej historii.
    """
    all_messages = rpg_database.get_history_with_embeddings()

    if not all_messages:
        return []

    # Przy krótkiej historii — po prostu zwróć wszystko
    total_k = RECENT_K + RELEVANT_K
    if len(all_messages) <= total_k:
        return [{"role": m["role"], "content": m["content"]} for m in all_messages]

    recent = all_messages[-RECENT_K:]
    older = all_messages[:-RECENT_K]

    # Starsze wiadomości z embeddingami (bez embeddingu są pomijane w retrieval)
    older_with_emb = [m for m in older if m["embedding"] is not None]

    if not older_with_emb:
        # Brak embeddingów — fallback do ostatnich total_k wiadomości
        return [{"role": m["role"], "content": m["content"]} for m in all_messages[-total_k:]]

    query_vec = _embed(query)

    scored = [
        (_cosine_sim(query_vec, np.frombuffer(m["embedding"], dtype=np.float32)), m)
        for m in older_with_emb
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [m for _, m in scored[:RELEVANT_K]]

    # Złącz i deduplikuj po id, posortuj chronologicznie
    combined = {m["id"]: m for m in relevant + recent}
    return [
        {"role": m["role"], "content": m["content"]}
        for m in sorted(combined.values(), key=lambda x: x["id"])
    ]
