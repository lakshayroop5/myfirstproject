"""
Tool hooks system for automatic tool integration.

This module provides decorators and functions that allow any task to easily
access and execute tools without manual setup.
"""

import asyncio
import functools
from typing import Any, Dict, List, Optional, Callable, Union
import logging

from .base import Tool, ToolResult, ToolRegistry, get_tool_registry
from .config import load_tools_config, get_tool_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ToolContext:
    """Context object that provides access to tools within tasks."""
    
    def __init__(self, registry: ToolRegistry = None):
        """
        Initialize tool context.
        
        Args:
            registry: Tool registry to use (defaults to global registry)
        """
        self.registry = registry or get_tool_registry()
        self._cache: Dict[str, Any] = {}
    
    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            ToolResult: Result of the tool execution
        """
        logger.debug(f"Executing tool: {tool_name} with params: {list(kwargs.keys())}")
        return await self.registry.execute_tool(tool_name, **kwargs)
    
    def execute_sync(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Synchronously execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            ToolResult: Result of the tool execution
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.execute(tool_name, **kwargs))
    
    def get_available_tools(self, category: str = None) -> List[str]:
        """
        Get list of available tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        return self.registry.list_tools(category)
    
    def get_tool_schema(self, tool_name: str = None) -> Dict[str, Any]:
        """
        Get schema for tools.
        
        Args:
            tool_name: Optional specific tool name
            
        Returns:
            Tool schema(s)
        """
        if tool_name:
            tool = self.registry.get_tool(tool_name)
            return tool.get_schema() if tool else {}
        return self.registry.get_schema()
    
    def cache_set(self, key: str, value: Any) -> None:
        """Set a value in the tool context cache."""
        self._cache[key] = value
    
    def cache_get(self, key: str, default: Any = None) -> Any:
        """Get a value from the tool context cache."""
        return self._cache.get(key, default)
    
    def cache_clear(self) -> None:
        """Clear the tool context cache."""
        self._cache.clear()


def tool_hook(func: Callable = None, *, auto_load: bool = True, config_dir: str = None) -> Callable:
    """
    Decorator that provides tool access to any function.
    
    This decorator automatically injects a 'tools' parameter into the decorated
    function, providing access to all configured tools.
    
    Args:
        func: Function to decorate
        auto_load: Whether to automatically load tool configurations
        config_dir: Directory containing tool configurations
        
    Returns:
        Decorated function with tool access
        
    Example:
        @tool_hook
        async def my_task(ctx, tools):
            # Use LLM tool
            llm_result = await tools.execute('openai', 
                prompt="Hello, world!", 
                max_tokens=100
            )
            
            # Use database tool
            db_result = await tools.execute('postgresql',
                query="SELECT * FROM users LIMIT 10"
            )
            
            return {"llm": llm_result.data, "db": db_result.data}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Auto-load tools if requested
            if auto_load:
                await _ensure_tools_loaded(config_dir)
            
            # Create tool context
            tools = ToolContext()
            
            # Inject tools into function
            if asyncio.iscoroutinefunction(func):
                return await func(*args, tools=tools, **kwargs)
            else:
                return func(*args, tools=tools, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Auto-load tools if requested
            if auto_load:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(_ensure_tools_loaded(config_dir))
            
            # Create tool context
            tools = ToolContext()
            
            # Inject tools into function
            return func(*args, tools=tools, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


async def _ensure_tools_loaded(config_dir: str = None) -> None:
    """Ensure tools are loaded and registered."""
    registry = get_tool_registry()
    
    # Check if tools are already loaded
    if registry.list_tools():
        return
    
    # Load configurations
    configs = load_tools_config(config_dir)
    
    # Always register basic tools even if no config
    await _register_basic_tools()
    
    # Import and register configured tools
    await _register_tools_from_config(configs)


async def _register_basic_tools() -> None:
    """Register basic tools that should always be available."""
    registry = get_tool_registry()
    
    # Register file manager tool (always available)
    from .utils import FileTool
    file_tool = FileTool('file_manager', {
        'base_path': '.',
        'max_file_size': 10 * 1024 * 1024,
        'allowed_extensions': []
    })
    registry.register(file_tool, 'utility')
    
    # Register HTTP client tool (always available)
    from .api import HTTPTool
    http_tool = HTTPTool('http_client', {
        'verify_ssl': True,
        'timeout': 30,
        'headers': {'User-Agent': 'Agent-SDK/1.0'}
    })
    registry.register(http_tool, 'api')


async def _register_tools_from_config(configs: Dict[str, Any]) -> None:
    """Register tools based on configuration."""
    registry = get_tool_registry()
    
    for tool_name, config in configs.items():
        if not config.enabled:
            logger.debug(f"Skipping disabled tool: {tool_name}")
            continue
        
        try:
            # Import and create tool based on type
            tool = await _create_tool(config)
            if tool:
                registry.register(tool, config.category)
                logger.info(f"Registered tool: {tool_name} ({config.type})")
        
        except Exception as e:
            logger.error(f"Failed to register tool {tool_name}: {e}")


async def _create_tool(config) -> Optional[Tool]:
    """Create a tool instance based on configuration."""
    tool_type = config.type.lower()
    
    try:
        if tool_type == 'llm':
            return await _create_llm_tool(config)
        elif tool_type == 'database':
            return await _create_database_tool(config)
        elif tool_type == 'api':
            return await _create_api_tool(config)
        elif tool_type == 'utility':
            return await _create_utility_tool(config)
        else:
            logger.warning(f"Unknown tool type: {tool_type}")
            return None
    
    except Exception as e:
        logger.error(f"Error creating tool {config.name}: {e}")
        return None


async def _create_llm_tool(config) -> Optional[Tool]:
    """Create an LLM tool based on configuration."""
    from .llm import OpenAITool, GeminiTool, MistralTool, AnthropicTool
    
    tool_name = config.name.lower()
    
    if 'openai' in tool_name or 'gpt' in tool_name:
        return OpenAITool(config.name, config.config)
    elif 'gemini' in tool_name:
        return GeminiTool(config.name, config.config)
    elif 'mistral' in tool_name:
        return MistralTool(config.name, config.config)
    elif 'anthropic' in tool_name or 'claude' in tool_name:
        return AnthropicTool(config.name, config.config)
    else:
        logger.warning(f"Unknown LLM tool: {tool_name}")
        return None


async def _create_database_tool(config) -> Optional[Tool]:
    """Create a database tool based on configuration."""
    from .database import PostgreSQLTool, Neo4jTool, MongoDBTool
    
    tool_name = config.name.lower()
    
    if 'postgres' in tool_name or 'postgresql' in tool_name:
        return PostgreSQLTool(config.name, config.config)
    elif 'neo4j' in tool_name:
        return Neo4jTool(config.name, config.config)
    elif 'mongo' in tool_name:
        return MongoDBTool(config.name, config.config)
    else:
        logger.warning(f"Unknown database tool: {tool_name}")
        return None


async def _create_api_tool(config) -> Optional[Tool]:
    """Create an API tool based on configuration."""
    from .api import HTTPTool, RestAPITool
    
    if config.config.get('rest_api'):
        return RestAPITool(config.name, config.config)
    else:
        return HTTPTool(config.name, config.config)


async def _create_utility_tool(config) -> Optional[Tool]:
    """Create a utility tool based on configuration."""
    from .utils import FileTool, EmailTool, SlackTool
    
    tool_name = config.name.lower()
    
    if 'file' in tool_name:
        return FileTool(config.name, config.config)
    elif 'email' in tool_name:
        return EmailTool(config.name, config.config)
    elif 'slack' in tool_name:
        return SlackTool(config.name, config.config)
    else:
        logger.warning(f"Unknown utility tool: {tool_name}")
        return None


# Convenience functions for direct tool access
async def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """
    Execute a tool directly.
    
    Args:
        tool_name: Name of the tool to execute
        **kwargs: Parameters for the tool
        
    Returns:
        ToolResult: Result of the tool execution
    """
    await _ensure_tools_loaded()
    registry = get_tool_registry()
    return await registry.execute_tool(tool_name, **kwargs)


def get_available_tools(category: str = None) -> List[str]:
    """
    Get list of available tools.
    
    Args:
        category: Optional category filter
        
    Returns:
        List of tool names
    """
    registry = get_tool_registry()
    return registry.list_tools(category)


def get_tool_schema(tool_name: str = None) -> Dict[str, Any]:
    """
    Get schema for tools.
    
    Args:
        tool_name: Optional specific tool name
        
    Returns:
        Tool schema(s)
    """
    registry = get_tool_registry()
    if tool_name:
        tool = registry.get_tool(tool_name)
        return tool.get_schema() if tool else {}
    return registry.get_schema()