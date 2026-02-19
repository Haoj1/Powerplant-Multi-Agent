"""
Lightweight embedding generation using sentence-transformers.
Supports local models, no API calls needed.
"""

from typing import List, Optional
import numpy as np


class EmbeddingModel:
    """Lightweight embedding model wrapper."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Args:
            model_name: Model name from sentence-transformers
                - "all-MiniLM-L6-v2" (default): 22MB, 384 dims, fast
                - "paraphrase-MiniLM-L3-v2": 17MB, 384 dims, faster but slightly worse
                - "all-mpnet-base-v2": 420MB, 768 dims, better quality
        """
        self.model_name = model_name
        self._model = None
        self._dimension = None
    
    def _load_model(self):
        """Lazy load model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                # Get embedding dimension
                test_embedding = self._model.encode("test", convert_to_numpy=True)
                self._dimension = len(test_embedding)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                )
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension
    
    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of text strings
            normalize: Whether to L2-normalize embeddings (default True for cosine similarity)
        
        Returns:
            numpy array of shape (n_texts, dimension)
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return embeddings
    
    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Encode a single text to embedding."""
        return self.encode([text], normalize=normalize)[0]


# Global singleton instance (lazy loaded)
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingModel:
    """Get or create global embedding model instance."""
    global _embedding_model
    if _embedding_model is None or _embedding_model.model_name != model_name:
        _embedding_model = EmbeddingModel(model_name)
    return _embedding_model
