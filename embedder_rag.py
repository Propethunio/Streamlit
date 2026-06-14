import faiss
import numpy as np
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings

_EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 150


class FAISSIndex:
    def __init__(self, faiss_index, metadata):
        self.index = faiss_index
        self.metadata = metadata

    def similarity_search(self, query_vector, k=3):
        _, indices = self.index.search(query_vector, k)
        return [
            self.metadata[idx]
            for idx in indices[0]
            if 0 <= idx < len(self.metadata)
        ]


@st.cache_resource
def _get_embeddings():
    """Ładuje model embeddingów raz i cachuje go przez cały czas życia aplikacji."""
    return HuggingFaceEmbeddings(
        model_name=_EMBED_MODEL_ID,
        model_kwargs={"device": "cpu", "trust_remote_code": True},
    )


def create_index(documents):
    """Tworzy indeks FAISS, dzieląc dokumenty na fragmenty po ~800 znaków."""
    embeddings = _get_embeddings()
    chunks, metadata = [], []

    for doc in documents:
        text = doc["text"]
        i = 0
        while i < len(text):
            chunk = text[i : i + _CHUNK_SIZE]
            if chunk.strip():
                chunks.append(chunk)
                metadata.append({"filename": doc["filename"], "text": chunk})
            i += _CHUNK_SIZE - _CHUNK_OVERLAP

    if not chunks:
        return None

    vectors = np.array([embeddings.embed_query(c) for c in chunks], dtype="float32")
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    return FAISSIndex(index, metadata)


def retrieve_docs(query, faiss_index, k=2):
    """Przeszukuje indeks FAISS na podstawie zapytania użytkownika."""
    embeddings = _get_embeddings()
    query_vec = np.array([embeddings.embed_query(query)], dtype="float32")
    return faiss_index.similarity_search(query_vec, k)
