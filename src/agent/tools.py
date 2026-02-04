"""Agent tools for querying the vector database."""
import logging
from typing import List, Dict

from src.database.chroma import ChromaDBClient

logger = logging.getLogger(__name__)


class VectorDBTool:
    """Tool for querying the vector database for document content."""
    
    def __init__(self, chroma_client: ChromaDBClient):
        """Initialize the tool with a ChromaDB client.
        
        Args:
            chroma_client: The ChromaDB client instance
        """
        self.chroma_client = chroma_client
    
    def query_vector_db(self, query: str, n_results: int = 5) -> str:
        """Query the vector database for relevant document content.
        
        This tool should be used when the user asks questions about uploaded
        PDF documents. It searches the vector database for relevant content
        and returns it formatted for the agent to use in answering.
        
        Args:
            query: The user's question or query
            n_results: Number of relevant chunks to retrieve (default: 5)
            
        Returns:
            Formatted string with relevant document content, or error message
        """
        try:
            logger.info(f"Querying vector DB with: {query}")
            
            # Check if database has any documents
            stats = self.chroma_client.get_stats()
            if stats.get("total_chunks", 0) == 0:
                return "No documents have been uploaded yet. Please upload a PDF first."
            
            # Query the database
            documents, metadatas = self.chroma_client.query(
                query_text=query,
                n_results=n_results
            )
            
            if not documents:
                return "No relevant information found in the uploaded documents."
            
            # Format the results
            formatted_results = self._format_results(documents, metadatas)
            
            logger.info(f"Retrieved {len(documents)} relevant chunks")
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error querying database: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _format_results(
        self,
        documents: List[str],
        metadatas: List[Dict]
    ) -> str:
        """Format query results for the agent.
        
        Args:
            documents: List of relevant document chunks
            metadatas: List of metadata for each chunk
            
        Returns:
            Formatted string with document content
        """
        formatted = "SEARCH RESULTS FROM UPLOADED DOCUMENTS:\n"
        formatted += "(Note: These are the most semantically similar chunks found. Verify they actually answer the query.)\n\n"
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
            source = meta.get("source", "Unknown")
            chunk_idx = meta.get("chunk_index", "?")
            
            formatted += f"--- Result {i} ---\n"
            formatted += f"Source: {source}\n"
            formatted += f"Chunk: {chunk_idx}\n"
            formatted += f"Content:\n{doc}\n"
            formatted += "-" * 80 + "\n\n"
        
        formatted += "\nIMPORTANT: Only use information from these results if it DIRECTLY answers the user's question. "
        formatted += "If the query asked about person/topic X but these results are about person/topic Y, "
        formatted += "you MUST tell the user that information about X was not found in the documents.\n"
        
        return formatted


def get_tool_definitions() -> List[Dict]:
    """Get the tool definitions for the Google ADK agent.
    
    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "query_vector_db",
            "description": (
                "Query the vector database to find relevant information from uploaded PDF documents. "
                "Use this tool when the user asks questions about document content, specific topics "
                "mentioned in documents, or requests information that would be in the uploaded PDFs. "
                "DO NOT use this tool for general questions, greetings, or questions about AI/technology "
                "that are not related to the uploaded documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question or query to search for in the documents"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of relevant document chunks to retrieve (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    ]
