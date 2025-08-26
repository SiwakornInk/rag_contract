from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import warnings
import torch

warnings.filterwarnings('ignore')

class EmbeddingGenerator:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        # Check GPU availability
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        if self.device == 'cuda':
            print(f"✓ Embeddings will use GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠ Embeddings will use CPU")
        
        # Load model with device specification
        self.model = SentenceTransformer(model_name, device=self.device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        print(f"Loaded embedding model: {model_name}")
        print(f"Embedding dimension: {self.dimension}")
        print(f"Max sequence length: {self.model.max_seq_length}")
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> Union[List[float], List[List[float]]]:
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        # Encode with GPU optimization
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size if self.device == 'cuda' else 8,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        if single_text:
            return embeddings[0].tolist()
        return [emb.tolist() for emb in embeddings]
    
    def get_dimension(self) -> int:
        return self.dimension