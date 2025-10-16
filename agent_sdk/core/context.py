"""Context management utilities for the agentic framework."""

from typing import Dict, Any, TypeVar, Union
from dataclasses import dataclass, field

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class Context:
    """Immutable context container for agent processing."""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context."""
        return self.data.get(key, default)
    
    def with_data(self, **kwargs) -> 'Context':
        """Create new context with additional data."""
        new_data = {**self.data, **kwargs}
        return Context(data=new_data)
    
    def merge(self, other: Union['Context', Dict[str, Any]]) -> 'Context':
        """Merge with another context or dictionary."""
        if isinstance(other, Context):
            other_data = other.data
        else:
            other_data = other
            
        return merge_context(self, other_data)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.data[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in context."""
        return key in self.data


def merge_context(ctx: Context, output: Any) -> Context:
    """
    Merge output into context using functional approach.
    
    Args:
        ctx: Current context
        output: Output to merge (dict or other type)
        
    Returns:
        New context with merged data
    """
    # Use shallow copy to avoid issues with unpickleable objects
    new_data = dict(ctx.data)
    
    if isinstance(output, dict):
        new_data.update(output)
        logger.debug(f"Merged dict output with {len(output)} keys")
    else:
        # Store non-dict outputs under a type-based key
        key = f"result_{output.__class__.__name__}"
        new_data[key] = output
        logger.debug(f"Stored {type(output).__name__} output under key '{key}'")
    
    return Context(data=new_data)