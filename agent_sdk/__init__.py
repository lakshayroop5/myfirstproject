"""
Agent SDK - A functional programming framework for building agentic workflows.

This SDK provides a clean, functional approach to building agent systems
with support for async operations and modular stage-based processing.
"""

from .core.stages import Stage, perceive, reason, plan, act
from .core.spine import agentic_spine, agentic_spine_simple, agentic_spine_async, agentic_spine_async_prefect
from .core.context import Context, merge_context
from .core.decorators import stage_decorator, async_stage
from .core.state import (
    StageState, StageExecution, StageStateObserver, LoggingObserver, MetricsObserver,
    get_state_manager, configure_monitoring, get_workflow_status, get_metrics
)
from .utils.logging import get_logger, setup_logging

__version__ = "0.2.0"
__all__ = [
    # Core workflow components
    "Stage",
    "perceive", 
    "reason", 
    "plan", 
    "act",
    
    # Execution engines
    "agentic_spine",              # Prefect-powered version (sync)
    "agentic_spine_simple",       # Simple version without Prefect (sync)
    "agentic_spine_async",        # Async version (simple)
    "agentic_spine_async_prefect", # Async version with Prefect
    
    # Context management
    "Context",
    "merge_context",
    
    # Custom decorators
    "stage_decorator",
    "async_stage",
    
    # State monitoring
    "StageState",
    "StageExecution", 
    "StageStateObserver",
    "LoggingObserver",
    "MetricsObserver",
    "get_state_manager",
    "configure_monitoring",
    "get_workflow_status",
    "get_metrics",
    
    # Utilities
    "get_logger",
    "setup_logging"
]