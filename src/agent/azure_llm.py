"""Custom Azure OpenAI model wrapper for Google ADK."""
import inspect
import logging
from typing import Any, Dict, List, Optional

from google.adk.models import BaseLlm
from google.genai import types
from openai import AzureOpenAI
from pydantic import Field, PrivateAttr

logger = logging.getLogger(__name__)


class AzureOpenAIModel(BaseLlm):
    """Azure OpenAI model wrapper for Google ADK Agent."""
    
    # Private attributes (not part of Pydantic validation)
    _client: AzureOpenAI = PrivateAttr()
    _deployment_name: str = PrivateAttr()
    _tools_schema: List[Dict] = PrivateAttr(default_factory=list)
    _tools_map: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    def __init__(
        self,
        api_key: str,
        azure_endpoint: str,
        api_version: str,
        deployment_name: str
    ):
        """Initialize Azure OpenAI model.
        
        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint URL
            api_version: API version
            deployment_name: Deployment name (model name in Azure)
        """
        # Initialize BaseLlm with model name
        super().__init__(model=deployment_name)
        
        # Set private attributes
        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version
        )
        self._deployment_name = deployment_name
        self._tools_schema = []
        self._tools_map = {}
        logger.info(f"Initialized Azure OpenAI model: {deployment_name}")
    
    def set_tools(self, tools: List[Any]):
        """Convert Python functions to OpenAI tool schemas.
        
        Args:
            tools: List of Python callable functions
        """
        self._tools_schema = []
        for tool in tools:
            if callable(tool):
                # Get function signature
                sig = inspect.signature(tool)
                params = {}
                required = []
                
                for param_name, param in sig.parameters.items():
                    # Get type hint
                    param_type = "string"  # default
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == float:
                            param_type = "number"
                        elif param.annotation == bool:
                            param_type = "boolean"
                    
                    params[param_name] = {"type": param_type}
                    
                    # Check if required (no default value)
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)
                
                # Create OpenAI function schema
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": tool.__doc__ or f"Call {tool.__name__}",
                        "parameters": {
                            "type": "object",
                            "properties": params,
                            "required": required
                        }
                    }
                }
                self._tools_schema.append(tool_schema)
                self._tools_map[tool.__name__] = tool  # Store the callable
                logger.info(f"Added tool schema for: {tool.__name__}")
        
        logger.info(f"Total tools configured: {len(self._tools_schema)}")
    
    def generate_content(
        self,
        prompt: Any,
        **kwargs
    ) -> str:
        """Generate content from the model (required by BaseLlm).
        
        Args:
            prompt: The input prompt (string, list of messages, or Content object)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        try:
            # Convert prompt to messages format
            messages = self._convert_prompt_to_messages(prompt)
            
            response = self._client.chat.completions.create(
                model=self._deployment_name,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    async def generate_content_async(
        self,
        prompt: Any,
        **kwargs
    ):
        """Async generator for content generation (required by BaseLlm).
        
        Args:
            prompt: The input prompt (can be string or structured object)
            **kwargs: Additional generation parameters
            
        Yields:
            Response objects with required attributes
        """
        try:
            # Convert prompt to messages format
            messages = self._convert_prompt_to_messages(prompt)
            
            # Log for debugging
            logger.info(f"generate_content_async called with kwargs: {list(kwargs.keys())}")
            if 'tools' in kwargs:
                logger.info(f"Tools received: {kwargs['tools']}")
            
            # Remove 'stream' if present (we're not streaming yet)
            api_kwargs = {k: v for k, v in kwargs.items() if k != 'stream'}
            
            # Add tools if we have them configured
            if self._tools_schema:
                api_kwargs['tools'] = self._tools_schema
                api_kwargs['tool_choice'] = 'auto'
                logger.info(f"Adding {len(self._tools_schema)} tools to API call")
            
            # For now, generate synchronously and yield the result
            # In production, use async OpenAI client with streaming
            response = self._client.chat.completions.create(
                model=self._deployment_name,
                messages=messages,
                **api_kwargs
            )
            
            logger.info(f"OpenAI response finish_reason: {response.choices[0].finish_reason}")
            
            # Check if OpenAI wants to call a tool
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                import json
                logger.info(f"OpenAI returned {len(response.choices[0].message.tool_calls)} tool_calls")
                tool_call = response.choices[0].message.tool_calls[0]
                logger.info(f"Tool call: {tool_call.function.name}({tool_call.function.arguments})")
                
                # Execute the tool
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name in self._tools_map:
                    logger.info(f"Executing tool: {tool_name}")
                    tool_result = self._tools_map[tool_name](**tool_args)
                    logger.info(f"Tool result length: {len(str(tool_result))} chars")
                    
                    # Make a second API call with the tool results
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": tool_call.function.arguments
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })
                    
                    # Get final response from OpenAI
                    logger.info("Requesting final response with tool results")
                    final_response = self._client.chat.completions.create(
                        model=self._deployment_name,
                        messages=messages,
                        **api_kwargs
                    )
                    content_text = final_response.choices[0].message.content or ""
                    logger.info(f"Final response: {content_text[:100]}...")
                else:
                    logger.error(f"Tool {tool_name} not found in tools map")
                    content_text = f"Error: Tool {tool_name} not available"
                
                content_obj = types.Content(
                    parts=[types.Part(text=content_text)],
                    role="model"
                )
            else:
                # Regular text response
                content_text = response.choices[0].message.content or ""
                content_obj = types.Content(
                    parts=[types.Part(text=content_text)],
                    role="model"
                )
            
            # Create a minimal response-like object that works with Google ADK
            # Google ADK expects certain attributes but doesn't strictly enforce types
            class MinimalResponse:
                def __init__(self, content, usage):
                    self.content = content
                    self.finish_reason = "STOP"
                    self.partial = False
                    self.usage_metadata = types.GenerateContentResponseUsageMetadata(
                        prompt_token_count=usage.prompt_tokens if usage else 0,
                        candidates_token_count=usage.completion_tokens if usage else 0,
                        total_token_count=usage.total_tokens if usage else 0
                    )
                
                def model_dump(self, **kwargs):
                    """Return dict for Event validation - must include content."""
                    return {
                        'content': self.content,
                        'finish_reason': self.finish_reason,
                        'partial': self.partial,
                        'usage_metadata': {
                            'prompt_token_count': self.usage_metadata.prompt_token_count,
                            'candidates_token_count': self.usage_metadata.candidates_token_count,
                            'total_token_count': self.usage_metadata.total_token_count
                        }
                    }
            
            # Yield the response
            yield MinimalResponse(content_obj, response.usage)
        except Exception as e:
            logger.error(f"Error generating async response: {e}")
            raise
    
    def _convert_prompt_to_messages(self, prompt: Any) -> List[Dict[str, str]]:
        """Convert various prompt formats to OpenAI messages format.
        
        Args:
            prompt: Can be a string, list of messages, or Google ADK Content object
            
        Returns:
            List of message dictionaries
        """
        # If it's already a list of messages, return it
        if isinstance(prompt, list):
            return prompt
        
        # If it's a string, convert to user message
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        
        # If it's a Google ADK Content object or similar
        if hasattr(prompt, 'parts'):
            # Extract text from parts
            text_parts = []
            for part in prompt.parts:
                if hasattr(part, 'text'):
                    text_parts.append(part.text)
            
            role = getattr(prompt, 'role', 'user')
            content = "\n".join(text_parts) if text_parts else str(prompt)
            return [{"role": role, "content": content}]
        
        # Fallback: convert to string
        return [{"role": "user", "content": str(prompt)}]
    
    def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate a response from the model.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        return self.generate_content(prompt, **kwargs)
    
    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Any:
        """Generate a response with tool support.
        
        Args:
            messages: Conversation messages
            tools: Available tools for function calling
            **kwargs: Additional parameters
            
        Returns:
            Model response with potential tool calls
        """
        try:
            call_kwargs = {
                "model": self._deployment_name,
                "messages": messages,
                **kwargs
            }
            
            if tools:
                call_kwargs["tools"] = tools
                call_kwargs["tool_choice"] = "auto"
            
            response = self._client.chat.completions.create(**call_kwargs)
            return response
        except Exception as e:
            logger.error(f"Error generating with tools: {e}")
            raise
