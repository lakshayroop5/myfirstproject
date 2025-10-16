"""Additional decorators for the agentic framework."""

from typing import Callable, Any
from functools import wraps
import asyncio

from .stages import Stage
from ..utils.logging import get_logger

logger = get_logger(__name__)


def stage_decorator(stage: Stage) -> Callable:
    """Generic stage decorator factory."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            logger.debug(f"Executing {stage.name} stage: {fn.__name__}")
            return fn(*args, **kwargs)
        
        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"Executing async {stage.name} stage: {fn.__name__}")
            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            else:
                return fn(*args, **kwargs)
        
        # Choose wrapper based on function type
        wrapper = async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper
        setattr(wrapper, "_agent_stage", stage)
        setattr(wrapper, "_is_async", asyncio.iscoroutinefunction(fn))
        
        return wrapper
    return decorator


def async_stage(stage: Stage) -> Callable:
    """Decorator for async stage functions."""
    def decorator(fn: Callable) -> Callable:
        if not asyncio.iscoroutinefunction(fn):
            raise ValueError(f"Function {fn.__name__} must be async for async_stage decorator")
        
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Executing async {stage.name} stage: {fn.__name__}")
            return await fn(*args, **kwargs)
        
        setattr(wrapper, "_agent_stage", stage)
        setattr(wrapper, "_is_async", True)
        return wrapper
    return decorator