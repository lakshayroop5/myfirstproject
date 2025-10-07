"""
Unit Converter Application Package - Functional approach.

Exports all core components using functional composition.
"""

from functools import partial
from .unit_converter_controller import UnitConverterController
from .unit_models import UnitConversion, UnitCategory, create_valid_conversion, create_invalid_conversion
from .unit_tools import LengthTool, WeightTool, TemperatureTool, VolumeTool, TimeTool, SpeedTool
from .unit_factories import UnitToolFactory, UnitPerceiverFactory
from .unit_planner import UnitPlanner
from .unit_reasoner import UnitReasoner
from .unit_routing import UnitRouter

__version__ = '1.0.0'
__author__ = 'Pipeline Executor Team'

# Functional exports
__all__ = [
    # Core controller
    'UnitConverterController',
    
    # Models
    'UnitConversion',
    'UnitCategory',
    'create_valid_conversion',
    'create_invalid_conversion',
    
    # Tools
    'LengthTool',
    'WeightTool',
    'TemperatureTool',
    'VolumeTool',
    'TimeTool',
    'SpeedTool',
    
    # Components
    'UnitToolFactory',
    'UnitPerceiverFactory',
    'UnitPlanner',
    'UnitReasoner',
    'UnitRouter',
]


# Functional factory helpers
def create_controller_with_defaults(**kwargs):
    """Create controller with default settings using partial application."""
    defaults = {'timeout': 10, 'debug': False}
    config = {**defaults, **kwargs}
    return UnitConverterController(**config)


def create_tool_factory():
    """Create tool factory using functional approach."""
    return UnitToolFactory()


def create_perceiver_factory():
    """Create perceiver factory using functional approach."""
    return UnitPerceiverFactory()


# Add functional helpers to exports
__all__.extend([
    'create_controller_with_defaults',
    'create_tool_factory',
    'create_perceiver_factory',
])
