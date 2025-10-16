"""
Base classes for the tools system.

This module defines the core interfaces and base classes for all tools
in the agent SDK.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    status: ToolStatus
    data: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if the tool execution was successful."""
        return self.status == ToolStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """Check if the tool execution failed."""
        return self.status == ToolStatus.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "error": str(self.error) if self.error else None,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class ToolError(Exception):
    """Base exception for tool-related errors."""
    
    def __init__(self, message: str, tool_name: str = None, original_error: Exception = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error


class Tool(ABC):
    """Base class for all tools."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        Initialize the tool.
        
        Args:
            name: Unique name for the tool
            config: Configuration dictionary for the tool
        """
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.timeout = self.config.get("timeout", 30.0)
        self.retry_count = self.config.get("retry_count", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: Result of the tool execution
        """
        pass
    
    def execute_sync(self, **kwargs) -> ToolResult:
        """
        Synchronous wrapper for tool execution.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: Result of the tool execution
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.execute(**kwargs))
    
    async def _execute_with_retry(self, **kwargs) -> ToolResult:
        """Execute tool with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_count + 1):
            try:
                start_time = time.time()
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    self.execute(**kwargs),
                    timeout=self.timeout
                )
                
                result.execution_time = time.time() - start_time
                return result
                
            except asyncio.TimeoutError:
                error = ToolError(f"Tool {self.name} timed out after {self.timeout}s", self.name)
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.TIMEOUT,
                    error=error,
                    execution_time=self.timeout
                )
                
            except Exception as e:
                last_error = e
                if attempt < self.retry_count:
                    logger.warning(f"Tool {self.name} failed (attempt {attempt + 1}), retrying in {self.retry_delay}s: {e}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Tool {self.name} failed after {self.retry_count + 1} attempts: {e}")
        
        # All retries failed
        tool_error = ToolError(f"Tool {self.name} failed after retries", self.name, last_error)
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.ERROR,
            error=tool_error,
            execution_time=time.time() - start_time if 'start_time' in locals() else 0.0
        )
    
    def validate_config(self) -> bool:
        """
        Validate tool configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema for documentation and validation.
        
        Returns:
            Dict: Tool schema including parameters and description
        """
        return {
            "name": self.name,
            "description": self.__doc__ or f"Tool: {self.name}",
            "parameters": {},
            "required": [],
            "examples": []
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
        
    def register(self, tool: Tool, category: str = "general") -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
            category: Category for organizing tools
        """
        if not tool.enabled:
            logger.info(f"Tool {tool.name} is disabled, skipping registration")
            return
            
        if not tool.validate_config():
            logger.error(f"Tool {tool.name} has invalid configuration, skipping registration")
            return
            
        self._tools[tool.name] = tool
        
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name} in category: {category}")
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            
            # Remove from categories
            for category, tools in self._categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)
                    
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self, category: str = None) -> List[str]:
        """
        List available tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """
        List available categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """
        Get all tools in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of Tool instances
        """
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            ToolResult: Result of the tool execution
        """
        tool = self.get_tool(tool_name)
        if not tool:
            error = ToolError(f"Tool '{tool_name}' not found", tool_name)
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=error
            )
        
        return await tool._execute_with_retry(**kwargs)
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get schema for all registered tools.
        
        Returns:
            Dict: Complete schema of all tools
        """
        return {
            "tools": {name: tool.get_schema() for name, tool in self._tools.items()},
            "categories": self._categories
        }


# Global tool registry instance
_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry