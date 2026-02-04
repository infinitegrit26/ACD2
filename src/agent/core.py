"""Smart Agent setup with Google ADK and Azure OpenAI."""
import json
import logging
import uuid
from typing import Dict, List, Optional

from google.adk import Agent, Runner
from google.genai import types

from src.config import get_config
from src.database.chroma import ChromaDBClient
from src.agent.tools import VectorDBTool
from src.agent.azure_llm import AzureOpenAIModel

logger = logging.getLogger(__name__)


class PDFChatAgent:
    """Smart agent that handles PDF document queries using Google ADK."""
    
    def __init__(self, chroma_client: ChromaDBClient):
        """Initialize the PDF Chat Agent with Google ADK.
        
        Args:
            chroma_client: ChromaDB client for vector operations
        """
        self.config = get_config()
        self.chroma_client = chroma_client
        self.vector_tool = VectorDBTool(chroma_client)
        
        # System prompt for smart routing
        system_instruction = """You are a helpful AI assistant with access to uploaded PDF documents.

IMPORTANT: You have access to a function called 'query_vector_db' to search through uploaded PDFs.

ROUTING RULES:
1. For general questions or greetings (like "hi", "hello", "how are you"), respond directly without calling any functions.
2. When the user asks about specific content, people, or topics that might be in the documents, call the query_vector_db function.

Examples of when TO call query_vector_db:
- "What experience does [name] have?"
- "Tell me about [topic] in the documents"
- "Find information about [anything]"
- "Summarize the document"

When you get results from query_vector_db:
- Provide information based ONLY on what was found
- If nothing relevant found, clearly state that
- Never mix up people or topics

Be concise and helpful."""
        
        # Create Google ADK Agent with Azure OpenAI model
        try:
            # Initialize custom Azure OpenAI model wrapper
            model = AzureOpenAIModel(
                api_key=self.config.openai_api_key,
                azure_endpoint=self.config.openai_api_endpoint,
                api_version=self.config.openai_api_version,
                deployment_name=self.config.llm_model
            )
            
            # Get tool function
            tool_function = self._create_tool_function()
            
            # Configure tools in the model for OpenAI function calling
            model.set_tools([tool_function])
            
            # Create agent with tool
            self.agent = Agent(
                name="PDFChatAgent",
                model=model,
                instruction=system_instruction,
                tools=[tool_function]
            )
            
            # Create runner for the agent
            from google.adk.sessions import InMemorySessionService
            session_service = InMemorySessionService()
            
            self.runner = Runner(
                app_name="PDFChatApp",
                agent=self.agent,
                session_service=session_service,
                auto_create_session=True
            )
            
            # Generate a session ID for this agent instance
            self.session_id = str(uuid.uuid4())
            self.user_id = "user"
            
            logger.info(f"Google ADK Agent initialized with Azure OpenAI: {self.config.llm_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Google ADK Agent: {e}")
            raise
    
    def _create_tool_function(self):
        """Create the tool function for Google ADK.
        
        Returns:
            Callable tool function for the agent
        """
        def query_vector_db(query: str, n_results: int = 5) -> str:
            """Search uploaded PDF documents for relevant information.
            
            Args:
                query: The search query to find relevant document content
                n_results: Number of document chunks to retrieve (default: 5)
            
            Returns:
                Formatted string with relevant document content
            """
            logger.info(f"Tool executed: query_vector_db(query='{query}')")
            result = self.vector_tool.query_vector_db(query, n_results)
            logger.info(f"Tool result length: {len(result)} characters")
            return result
        
        return query_vector_db
    
    
    def chat(self, user_message: str, history: Optional[List[Dict]] = None) -> str:
        """Process a user message and return the agent's response.
        
        Args:
            user_message: The user's input message
            history: Optional conversation history (not used in stateless mode)
            
        Returns:
            The agent's response as a string
        """
        try:
            logger.info(f"Processing user message: {user_message[:100]}...")
            
            # Create Content object for the message
            message_content = types.Content(
                role='user',
                parts=[types.Part(text=user_message)]
            )
            
            # Use Google ADK Runner to process the message
            event_generator = self.runner.run(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=message_content
            )
            
            # Collect response from events
            response_text = ""
            for event in event_generator:
                # Extract text from events (agent response)
                response_part = self._extract_from_event(event)
                if response_part:
                    response_text += response_part
            
            logger.info(f"Agent response: {response_text[:200] if response_text else '(empty)'}...")
            return response_text.strip() if response_text else "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def _extract_from_event(self, event) -> str:
        """Extract text content from Google ADK event.
        
        Args:
            event: Event object from Runner
            
        Returns:
            Extracted text or empty string
        """
        try:
            # Check for model response event with content
            if hasattr(event, 'content') and event.content:
                content = event.content
                if hasattr(content, 'parts'):
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        return "".join(text_parts)
                
        except Exception as e:
            logger.debug(f"Error extracting text from event: {e}")
        
        return ""
    
    def get_stats(self) -> Dict:
        """Get statistics about the agent and database.
        
        Returns:
            Dictionary with statistics
        """
        db_stats = self.chroma_client.get_stats()
        return {
            "model": f"Azure OpenAI: {self.config.llm_model}",
            "embedding_model": self.config.embedding_model,
            "database": db_stats
        }


def create_agent(chroma_client: ChromaDBClient) -> PDFChatAgent:
    """Factory function to create a PDF Chat Agent.
    
    Args:
        chroma_client: Initialized ChromaDB client
        
    Returns:
        Configured PDFChatAgent instance
    """
    return PDFChatAgent(chroma_client)
