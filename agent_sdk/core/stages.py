"""Stage definitions and decorators for the agentic framework."""

from enum import Enum, auto
from typing import Callable
from functools import wraps

from ..utils.logging import get_logger

logger = get_logger(__name__)


class Stage(Enum):
    """Enumeration of agent processing stages."""
    PERCEIVE = auto()
    REASON = auto() 
    PLAN = auto()
    ACT = auto()


def _create_stage_decorator(stage: Stage) -> Callable:
    """Create a stage decorator for the given stage type."""
    def decorator(fn: Callable) -> Callable:
        import asyncio
        
        if asyncio.iscoroutinefunction(fn):
            # Async function wrapper
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                logger.debug(f"Executing async {stage.name} stage: {fn.__name__}")
                return await fn(*args, **kwargs)
            
            setattr(async_wrapper, "_agent_stage", stage)
            return async_wrapper
        else:
            # Sync function wrapper
            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                logger.debug(f"Executing {stage.name} stage: {fn.__name__}")
                return fn(*args, **kwargs)
            
            setattr(sync_wrapper, "_agent_stage", stage)
            return sync_wrapper
    return decorator


# Stage decorators
perceive = _create_stage_decorator(Stage.PERCEIVE)
reason = _create_stage_decorator(Stage.REASON)
plan = _create_stage_decorator(Stage.PLAN)
act = _create_stage_decorator(Stage.ACT)