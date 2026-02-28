import os
import json
import numpy as np
from typing import List, Dict, Any

class SimpleVectorStore:
    def __init__(self, file_path="data/memory.json", embedding_dim=1536):
        self.file_path = file_path
        self.embedding_dim = embedding_dim
        self.documents = [] # List of {'text': str, 'metadata': dict, 'embedding': list}
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data
            except Exception as e:
                print(f"Error loading memory: {e}")
                self.documents = []

    def save(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def add(self, text: str, embedding: List[float], metadata: Dict[str, Any] = None):
        if not embedding:
             print("Warning: Attempted to add document without embedding.")
             return

        doc = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        self.documents.append(doc)
        self.save()

    def search(self, query_embedding: List[float], top_k=3, threshold=0.0) -> List[Dict]:
        if not self.documents:
            return []

        if not query_embedding:
            return []

        # Filter out docs with invalid embeddings
        valid_docs = [d for d in self.documents if d.get("embedding") and len(d["embedding"]) == len(query_embedding)]

        if not valid_docs:
            return []

        embeddings = np.array([d["embedding"] for d in valid_docs])
        query = np.array(query_embedding)

        # Cosine Similarity: (A . B) / (||A|| * ||B||)
        norm_docs = np.linalg.norm(embeddings, axis=1)
        norm_query = np.linalg.norm(query)

        # Avoid division by zero
        norm_docs[norm_docs == 0] = 1e-10
        if norm_query == 0:
            norm_query = 1e-10

        similarities = np.dot(embeddings, query) / (norm_docs * norm_query)

        # Get top K indices
        # argsort sorts in ascending order, so we take the last k and reverse
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score >= threshold:
                results.append({
                    "text": valid_docs[idx]["text"],
                    "metadata": valid_docs[idx]["metadata"],
                    "score": float(score)
                })

        return results
