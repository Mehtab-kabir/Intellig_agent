"""
Pinecone vector store service for document embeddings.
"""
import os
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Manages Pinecone vector store operations:
    - Initialize/create index
    - Generate embeddings using HuggingFace
    - Upsert document vectors
    - Query similar documents
    """
    
    # Using free HuggingFace model
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384
    
    def __init__(self):
        self._pc = None
        self._index = None
        self._embedder = None
        self._index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'legal-docs')
    
    @property
    def pc(self) -> Pinecone:
        """Lazy load Pinecone client."""
        if self._pc is None:
            api_key = getattr(settings, 'PINECONE_API_KEY', None)
            if not api_key:
                raise ValueError("PINECONE_API_KEY not configured in settings")
            self._pc = Pinecone(api_key=api_key)
        return self._pc
    
    @property
    def index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self._index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self._index_name}")
                self.pc.create_index(
                    name=self._index_name,
                    dimension=self.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            self._index = self.pc.Index(self._index_name)
        return self._index
    
    @property
    def embedder(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self._embedder is None:
            logger.info(f"Loading embedding model: {self.EMBEDDING_MODEL}")
            self._embedder = SentenceTransformer(self.EMBEDDING_MODEL)
        return self._embedder
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.embedder.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch)."""
        embeddings = self.embedder.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def upsert_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100):
        """
        Upsert documents to Pinecone.
        
        Args:
            documents: List of dicts with 'id', 'text', 'metadata'
            batch_size: Number of vectors to upsert at once
        """
        if not documents:
            return
        
        # Generate embeddings for all texts
        texts = [doc['text'] for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        # Prepare vectors for upsert
        vectors = []
        for doc, embedding in zip(documents, embeddings):
            vectors.append({
                'id': doc['id'],
                'values': embedding,
                'metadata': doc['metadata']
            })
        
        # Batch upsert
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.debug(f"Upserted batch {i//batch_size + 1}")
        
        logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
    
    def query(
        self, 
        query_text: str, 
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone for similar documents.
        
        Args:
            query_text: The search query
            top_k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)
        
        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter
        )
        
        # Format results
        documents = []
        for match in results.matches:
            documents.append({
                'id': match.id,
                'score': match.score,
                'metadata': match.metadata,
                'text': match.metadata.get('text', '')
            })
        
        return documents
    
    def delete_document(self, document_id: str):
        """Delete all vectors for a document."""
        # Delete by metadata filter
        self.index.delete(
            filter={"document_id": {"$eq": document_id}}
        )
        logger.info(f"Deleted vectors for document: {document_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = self.index.describe_index_stats()
        return {
            'total_vectors': stats.total_vector_count,
            'dimension': stats.dimension,
            'index_fullness': stats.index_fullness
        }
