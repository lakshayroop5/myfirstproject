"""
LLM (Large Language Model) tools for various providers.

This module provides tools for interacting with different LLM providers
including OpenAI, Google Gemini, Mistral, and Anthropic.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
import logging

from .base import Tool, ToolResult, ToolStatus, ToolError

logger = logging.getLogger(__name__)


class BaseLLMTool(Tool):
    """Base class for LLM tools."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get('api_key')
        self.model = config.get('model')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.7)
        self.top_p = config.get('top_p', 1.0)
        
    def validate_config(self) -> bool:
        """Validate LLM configuration."""
        if not self.api_key:
            logger.error(f"API key not provided for {self.name}")
            return False
        if not self.model:
            logger.error(f"Model not specified for {self.name}")
            return False
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """Get LLM tool schema."""
        return {
            "name": self.name,
            "description": f"LLM tool for {self.name}",
            "parameters": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send to the LLM",
                    "required": True
                },
                "system_prompt": {
                    "type": "string", 
                    "description": "System prompt for context",
                    "required": False
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                    "default": self.max_tokens
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0-2)",
                    "default": self.temperature
                },
                "stream": {
                    "type": "boolean",
                    "description": "Whether to stream the response",
                    "default": False
                }
            },
            "required": ["prompt"],
            "examples": [
                {
                    "prompt": "Explain quantum computing in simple terms",
                    "max_tokens": 200,
                    "temperature": 0.7
                }
            ]
        }


class OpenAITool(BaseLLMTool):
    """Tool for OpenAI GPT models."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get('base_url', 'https://ctonpsikytopenai.openai.azure.com/')
        self.organization = config.get('organization')
        
    async def execute(self, prompt: str, system_prompt: str = None, 
                     max_tokens: int = None, temperature: float = None,
                     stream: bool = False, **kwargs) -> ToolResult:
        """
        Execute OpenAI API call.
        
        Args:
            prompt: The main prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with the LLM response
        """
        try:
            # Import OpenAI client
            try:
                from openai import AsyncOpenAI, AzureOpenAI
            except ImportError:
                raise ToolError("OpenAI library not installed. Run: pip install openai", self.name)
            
            # Initialize client
            # client = AsyncOpenAI(
            #     api_key=self.api_key,
            #     base_url=self.base_url,
            #     organization=self.organization
            # )
            client = AzureOpenAI(
                azure_endpoint=self.base_url,
                api_key=self.api_key,
                api_version="2024-05-01-preview"
            )
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare parameters
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "top_p": self.top_p,
                "stream": stream
            }
            
            # Add any additional parameters
            params.update(kwargs)
            
            # Make API call
            if stream:
                response_text = ""
                async for chunk in await client.chat.completions.create(**params):
                    if chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                
                result_data = {
                    "response": response_text,
                    "model": self.model,
                    "stream": True
                }
            else:
                response = await client.chat.completions.create(**params)
                result_data = {
                    "response": response.choices[0].message.content,
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"OpenAI API error: {e}", self.name, e)
            )


class GeminiTool(BaseLLMTool):
    """Tool for Google Gemini models."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
    async def execute(self, prompt: str, system_prompt: str = None,
                     max_tokens: int = None, temperature: float = None,
                     **kwargs) -> ToolResult:
        """
        Execute Gemini API call.
        
        Args:
            prompt: The main prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with the LLM response
        """
        try:
            # Import Google AI client
            try:
                import google.generativeai as genai
            except ImportError:
                raise ToolError("Google AI library not installed. Run: pip install google-generativeai", self.name)
            
            # Configure API
            genai.configure(api_key=self.api_key)
            
            # Initialize model
            model = genai.GenerativeModel(self.model)
            
            # Prepare prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
            
            # Generate response
            response = await model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens or self.max_tokens,
                    temperature=temperature if temperature is not None else self.temperature,
                    top_p=self.top_p
                )
            )
            
            result_data = {
                "response": response.text,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
                },
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None
            }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Gemini API error: {e}", self.name, e)
            )


class MistralTool(BaseLLMTool):
    """Tool for Mistral AI models."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
    async def execute(self, prompt: str, system_prompt: str = None,
                     max_tokens: int = None, temperature: float = None,
                     stream: bool = False, **kwargs) -> ToolResult:
        """
        Execute Mistral API call.
        
        Args:
            prompt: The main prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with the LLM response
        """
        try:
            # Import Mistral client
            try:
                from mistralai.async_client import MistralAsyncClient
                from mistralai.models.chat_completion import ChatMessage
            except ImportError:
                raise ToolError("Mistral AI library not installed. Run: pip install mistralai", self.name)
            
            # Initialize client
            client = MistralAsyncClient(api_key=self.api_key)
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=prompt))
            
            # Make API call
            if stream:
                response_text = ""
                async for chunk in client.chat_stream(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=temperature if temperature is not None else self.temperature
                ):
                    if chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                
                result_data = {
                    "response": response_text,
                    "model": self.model,
                    "stream": True
                }
            else:
                response = await client.chat(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=temperature if temperature is not None else self.temperature
                )
                
                result_data = {
                    "response": response.choices[0].message.content,
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"Mistral API error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Mistral API error: {e}", self.name, e)
            )


class AnthropicTool(BaseLLMTool):
    """Tool for Anthropic Claude models."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
    async def execute(self, prompt: str, system_prompt: str = None,
                     max_tokens: int = None, temperature: float = None,
                     stream: bool = False, **kwargs) -> ToolResult:
        """
        Execute Anthropic API call.
        
        Args:
            prompt: The main prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with the LLM response
        """
        try:
            # Import Anthropic client
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ToolError("Anthropic library not installed. Run: pip install anthropic", self.name)
            
            # Initialize client
            client = AsyncAnthropic(api_key=self.api_key)
            
            # Prepare parameters
            params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            if system_prompt:
                params["system"] = system_prompt
            
            # Make API call
            if stream:
                response_text = ""
                async with client.messages.stream(**params) as stream:
                    async for text in stream.text_stream:
                        response_text += text
                
                result_data = {
                    "response": response_text,
                    "model": self.model,
                    "stream": True
                }
            else:
                response = await client.messages.create(**params)
                
                result_data = {
                    "response": response.content[0].text,
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    },
                    "stop_reason": response.stop_reason
                }
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"Anthropic API error: {e}", self.name, e)
            )