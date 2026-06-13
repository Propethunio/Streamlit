import faiss
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

class FAISSIndex:
    def __init__(self, faiss_index, metadata):
        self.index = faiss_index
        self.metadata = metadata

    def similarity_search(self, query, k=3):
        D, I = self.index.search(query, k)
        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.metadata):
                results.append(self.metadata[idx])
        return results

embed_model_id = "sentence-transformers/all-MiniLM-L6-v2" # nazwa modelu
model_kwargs = {"device": "cpu", "trust_remote_code": True}

def create_index(documents):
    """Tworzy indeks FAISS, dzieląc dokumenty na mniejsze fragmenty."""
    embeddings = HuggingFaceEmbeddings(model_name=embed_model_id, model_kwargs=model_kwargs)
    
    chunks = []
    metadata = []
    
    # Podział dużego tekstu na fragmenty po ok. 800 znaków (z zakładką 150)
    for doc in documents:
        text_content = doc["text"]
        chunk_size = 800
        overlap = 150
        i = 0
        while i < len(text_content):
            chunk = text_content[i:i+chunk_size]
            if chunk.strip():
                chunks.append(chunk)
                metadata.append({"filename": doc["filename"], "text": chunk})
            i += (chunk_size - overlap)

    if not chunks:
        return None

    # Generowanie wektorów i budowanie indeksu FAISS
    embeddings_matrix = [embeddings.embed_query(text) for text in chunks]
    embeddings_matrix = np.array(embeddings_matrix).astype("float32")

    dimension = embeddings_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_matrix)

    return FAISSIndex(index, metadata)

def retrieve_docs(query, faiss_index, k=2):
    """Przeszukuje bazę FAISS na podstawie zapytania użytkownika."""
    embeddings = HuggingFaceEmbeddings(model_name=embed_model_id, model_kwargs=model_kwargs)
    query_embedding = np.array([embeddings.embed_query(query)]).astype("float32")
    return faiss_index.similarity_search(query_embedding, k)