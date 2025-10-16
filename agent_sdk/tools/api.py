"""
API tools for HTTP requests and REST API interactions.

This module provides tools for making HTTP requests and interacting with
REST APIs with various authentication methods and response handling.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
import logging

from .base import Tool, ToolResult, ToolStatus, ToolError

logger = logging.getLogger(__name__)


class HTTPTool(Tool):
    """Tool for making HTTP requests."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get('base_url', '')
        self.headers = config.get('headers', {})
        self.auth = config.get('auth', {})
        self.verify_ssl = config.get('verify_ssl', True)
        
    def validate_config(self) -> bool:
        """Validate HTTP tool configuration."""
        return True  # HTTP tool has minimal requirements
    
    async def execute(self, method: str, url: str, params: Dict = None,
                     data: Any = None, json_data: Dict = None,
                     headers: Dict = None, auth: Dict = None,
                     timeout: float = None, **kwargs) -> ToolResult:
        """
        Execute HTTP request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL (can be relative to base_url)
            params: URL parameters
            data: Request body data
            json_data: JSON request body
            headers: Request headers
            auth: Authentication configuration
            timeout: Request timeout
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with HTTP response
        """
        try:
            # Import aiohttp
            try:
                import aiohttp
            except ImportError:
                raise ToolError("aiohttp library not installed. Run: pip install aiohttp", self.name)
            
            # Prepare URL
            if not url.startswith('http'):
                url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
            
            # Prepare headers
            request_headers = self.headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Prepare authentication
            auth_config = auth or self.auth
            auth_obj = None
            
            if auth_config:
                auth_type = auth_config.get('type', '').lower()
                if auth_type == 'basic':
                    auth_obj = aiohttp.BasicAuth(
                        auth_config['username'],
                        auth_config['password']
                    )
                elif auth_type == 'bearer':
                    request_headers['Authorization'] = f"Bearer {auth_config['token']}"
                elif auth_type == 'api_key':
                    key_name = auth_config.get('key_name', 'X-API-Key')
                    request_headers[key_name] = auth_config['api_key']
            
            # Prepare request parameters
            request_params = {
                'method': method.upper(),
                'url': url,
                'params': params,
                'headers': request_headers,
                'auth': auth_obj,
                'timeout': aiohttp.ClientTimeout(total=timeout or self.timeout),
                'ssl': self.verify_ssl
            }
            
            # Add body data
            if json_data is not None:
                request_params['json'] = json_data
            elif data is not None:
                request_params['data'] = data
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.request(**request_params) as response:
                    # Get response content
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if 'application/json' in content_type:
                        response_data = await response.json()
                    else:
                        response_data = await response.text()
                    
                    result_data = {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "data": response_data,
                        "url": str(response.url),
                        "method": method.upper()
                    }
                    
                    # Check if request was successful
                    if 200 <= response.status < 300:
                        status = ToolStatus.SUCCESS
                    else:
                        status = ToolStatus.ERROR
                        result_data["error"] = f"HTTP {response.status}: {response.reason}"
                    
                    return ToolResult(
                        tool_name=self.name,
                        status=status,
                        data=result_data
                    )
                    
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"HTTP request error: {e}", self.name, e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get HTTP tool schema."""
        return {
            "name": self.name,
            "description": "HTTP client tool for making web requests",
            "parameters": {
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "required": True,
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                },
                "url": {
                    "type": "string",
                    "description": "Request URL",
                    "required": True
                },
                "params": {
                    "type": "object",
                    "description": "URL parameters",
                    "required": False
                },
                "json_data": {
                    "type": "object",
                    "description": "JSON request body",
                    "required": False
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers",
                    "required": False
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds",
                    "required": False
                }
            },
            "required": ["method", "url"],
            "examples": [
                {
                    "method": "GET",
                    "url": "https://api.example.com/users",
                    "params": {"page": 1, "limit": 10}
                },
                {
                    "method": "POST",
                    "url": "https://api.example.com/users",
                    "json_data": {"name": "John Doe", "email": "john@example.com"}
                }
            ]
        }


class RestAPITool(HTTPTool):
    """Tool for REST API interactions with enhanced features."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_version = config.get('api_version', 'v1')
        self.rate_limit = config.get('rate_limit', {})
        self.retry_config = config.get('retry_config', {})
        
    async def execute(self, endpoint: str, method: str = "GET",
                     params: Dict = None, data: Any = None,
                     paginate: bool = False, **kwargs) -> ToolResult:
        """
        Execute REST API request with enhanced features.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            method: HTTP method
            params: Request parameters
            data: Request data
            paginate: Whether to handle pagination automatically
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with API response
        """
        try:
            # Prepare endpoint URL
            if self.api_version and not endpoint.startswith(f'/{self.api_version}'):
                endpoint = f"/{self.api_version}/{endpoint.lstrip('/')}"
            
            # Handle pagination if requested
            if paginate and method.upper() == "GET":
                return await self._paginated_request(endpoint, params, **kwargs)
            
            # Make single request
            return await super().execute(
                method=method,
                url=endpoint,
                params=params,
                json_data=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"REST API error: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=ToolError(f"REST API error: {e}", self.name, e)
            )
    
    async def _paginated_request(self, endpoint: str, params: Dict = None, **kwargs) -> ToolResult:
        """Handle paginated API requests."""
        all_data = []
        page = 1
        page_size = params.get('page_size', 100) if params else 100
        max_pages = kwargs.get('max_pages', 10)
        
        while page <= max_pages:
            # Prepare pagination parameters
            page_params = (params or {}).copy()
            page_params.update({
                'page': page,
                'page_size': page_size
            })
            
            # Make request
            result = await super().execute(
                method="GET",
                url=endpoint,
                params=page_params,
                **{k: v for k, v in kwargs.items() if k != 'max_pages'}
            )
            
            if not result.is_success:
                return result
            
            # Extract data
            response_data = result.data.get('data', {})
            
            if isinstance(response_data, dict):
                items = response_data.get('items', response_data.get('results', []))
                total_pages = response_data.get('total_pages', 1)
            else:
                items = response_data if isinstance(response_data, list) else []
                total_pages = 1
            
            all_data.extend(items)
            
            # Check if we have more pages
            if page >= total_pages or len(items) < page_size:
                break
            
            page += 1
        
        # Return combined result
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={
                "data": all_data,
                "total_items": len(all_data),
                "pages_fetched": page,
                "paginated": True
            }
        )
    
    async def get(self, endpoint: str, **kwargs) -> ToolResult:
        """Convenience method for GET requests."""
        return await self.execute(endpoint, "GET", **kwargs)
    
    async def post(self, endpoint: str, data: Dict = None, **kwargs) -> ToolResult:
        """Convenience method for POST requests."""
        return await self.execute(endpoint, "POST", data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Dict = None, **kwargs) -> ToolResult:
        """Convenience method for PUT requests."""
        return await self.execute(endpoint, "PUT", data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> ToolResult:
        """Convenience method for DELETE requests."""
        return await self.execute(endpoint, "DELETE", **kwargs)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get REST API tool schema."""
        return {
            "name": self.name,
            "description": "REST API client tool with pagination and enhanced features",
            "parameters": {
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint path",
                    "required": True
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "default": "GET",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                },
                "params": {
                    "type": "object",
                    "description": "Request parameters",
                    "required": False
                },
                "data": {
                    "type": "object",
                    "description": "Request data",
                    "required": False
                },
                "paginate": {
                    "type": "boolean",
                    "description": "Enable automatic pagination",
                    "default": False
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum pages to fetch when paginating",
                    "default": 10
                }
            },
            "required": ["endpoint"],
            "examples": [
                {
                    "endpoint": "/users",
                    "method": "GET",
                    "params": {"status": "active"},
                    "paginate": True
                },
                {
                    "endpoint": "/users",
                    "method": "POST",
                    "data": {"name": "John Doe", "email": "john@example.com"}
                }
            ]
        }