"""ChromaDB client and vector database operations."""
import hashlib
import logging
from typing import List, Dict, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from openai import OpenAI, AzureOpenAI

from src.config import get_config

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """Manages ChromaDB operations for PDF embeddings with persistence."""
    
    def __init__(self):
        """Initialize ChromaDB client with persistent storage."""
        self.config = get_config()
        
        # Initialize OpenAI or Azure OpenAI client
        
        self.openai_client = AzureOpenAI(
            api_key=self.config.openai_api_key,
            azure_endpoint=self.config.openai_api_endpoint,
            api_version=self.config.openai_api_version
        )
        
        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.config.chroma_persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize collection with OpenAI embeddings
        self.collection_name = "pdf_documents"
        self.collection = self._get_or_create_collection()
        
        logger.info(
            f"ChromaDB initialized with {self.collection.count()} existing documents"
        )
    
    def _get_or_create_collection(self):
        """Get or create the collection for PDF documents."""
        try:
            collection = self.client.get_collection(
                name=self.collection_name,
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "PDF document embeddings"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI's text-embedding-3-large."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def _compute_file_hash(self, filename: str, file_content: bytes) -> str:
        """Compute unique hash for a PDF file to detect duplicates."""
        content_hash = hashlib.sha256(file_content).hexdigest()
        return f"{filename}_{content_hash[:16]}"
    
    def is_file_processed(self, filename: str, file_content: bytes) -> bool:
        """Check if a file has already been processed."""
        file_hash = self._compute_file_hash(filename, file_content)
        
        try:
            results = self.collection.get(
                where={"file_hash": file_hash},
                limit=1
            )
            is_processed = len(results["ids"]) > 0
            
            if is_processed:
                logger.info(f"File already processed: {filename} (hash: {file_hash})")
            
            return is_processed
        except Exception as e:
            logger.error(f"Error checking file status: {e}")
            return False
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict],
        filename: str,
        file_content: bytes
    ) -> int:
        """Add document chunks to ChromaDB with embeddings.
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts for each chunk
            filename: Original PDF filename
            file_content: Raw PDF file content for hashing
            
        Returns:
            Number of chunks added
        """
        if not texts:
            logger.warning("No texts provided for embedding")
            return 0
        
        # Check for duplicates
        if self.is_file_processed(filename, file_content):
            logger.info(f"Skipping duplicate file: {filename}")
            return 0
        
        file_hash = self._compute_file_hash(filename, file_content)
        
        try:
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = [self._generate_embedding(text) for text in texts]
            
            # Add file_hash to all metadatas
            for metadata in metadatas:
                metadata["file_hash"] = file_hash
            
            # Generate unique IDs
            ids = [f"{file_hash}_chunk_{i}" for i in range(len(texts))]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully added {len(texts)} chunks from {filename}")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        n_results: int = 5
    ) -> Tuple[List[str], List[Dict]]:
        """Query the vector database for similar documents.
        
        Args:
            query_text: The query string
            n_results: Number of results to return
            
        Returns:
            Tuple of (documents, metadatas)
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query_text)
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            
            logger.info(f"Query returned {len(documents)} results")
            return documents, metadatas
            
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector database."""
        try:
            count = self.collection.count()
            
            # Get unique files
            all_items = self.collection.get()
            unique_files = set()
            if all_items["metadatas"]:
                for metadata in all_items["metadatas"]:
                    if "source" in metadata:
                        unique_files.add(metadata["source"])
            
            return {
                "total_chunks": count,
                "unique_files": len(unique_files),
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    def reset_database(self) -> None:
        """Reset the entire database (use with caution)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.warning("Database has been reset")
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            raise
