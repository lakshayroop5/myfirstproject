"""Router for directing conversions - Functional dispatch approach."""

import logging
from functools import partial
from .unit_models import UnitConversion, UnitCategory

logger = logging.getLogger(__name__)


class UnitRouter:
    """Routes conversions using functional dispatch."""
    
    def __init__(self, tool_factory):
        """Initialize router with functional dispatch table."""
        self._tool_factory = tool_factory
        
        # Functional dispatch table
        self._tool_map = {
            UnitCategory.LENGTH: tool_factory.create_length_tool,
            UnitCategory.WEIGHT: tool_factory.create_weight_tool,
            UnitCategory.TEMPERATURE: tool_factory.create_temperature_tool,
            UnitCategory.VOLUME: tool_factory.create_volume_tool,
            UnitCategory.TIME: tool_factory.create_time_tool,
            UnitCategory.SPEED: tool_factory.create_speed_tool,
        }
        
        logger.debug("UnitRouter initialized with functional dispatch")
    
    def route(self, conversion: UnitConversion):
        """Route conversion using functional dispatch."""
        tool_creator = self._tool_map.get(conversion.category)
        
        # Predicate-based logging
        log_warning = lambda: logger.warning(f"No tool available for category: {conversion.category}")
        _ = tool_creator or log_warning()
        
        return tool_creator() if tool_creator else None
