"""Factories for creating components - Functional caching approach."""

import logging
from typing import List
from functools import lru_cache
from .unit_tools import LengthTool, WeightTool, TemperatureTool, VolumeTool, TimeTool, SpeedTool
from .unit_perceivers import RegexUnitPerceiver, SimpleUnitPerceiver

logger = logging.getLogger(__name__)


class UnitToolFactory:
    """Factory with functional caching."""
    
    def __init__(self):
        self._tool_cache = {}
        logger.debug("UnitToolFactory initialized")
    
    def _get_or_create(self, key: str, creator):
        """Generic get-or-create using functional approach."""
        return self._tool_cache.get(key) or self._tool_cache.setdefault(key, creator())
    
    def create_length_tool(self) -> LengthTool:
        """Create or retrieve cached length tool."""
        return self._get_or_create('length', LengthTool)
    
    def create_weight_tool(self) -> WeightTool:
        """Create or retrieve cached weight tool."""
        return self._get_or_create('weight', WeightTool)
    
    def create_temperature_tool(self) -> TemperatureTool:
        """Create or retrieve cached temperature tool."""
        return self._get_or_create('temperature', TemperatureTool)
    
    def create_volume_tool(self) -> VolumeTool:
        """Create or retrieve cached volume tool."""
        return self._get_or_create('volume', VolumeTool)
    
    def create_time_tool(self) -> TimeTool:
        """Create or retrieve cached time tool."""
        return self._get_or_create('time', TimeTool)
    
    def create_speed_tool(self) -> SpeedTool:
        """Create or retrieve cached speed tool."""
        return self._get_or_create('speed', SpeedTool)
    
    def clear_cache(self):
        """Clear tool cache."""
        self._tool_cache.clear()
        logger.debug("Tool cache cleared")


class UnitPerceiverFactory:
    """Factory for creating perceivers using functional approach."""
    
    @staticmethod
    def create_perceivers() -> List:
        """Create all perceivers using functional composition."""
        perceiver_types = [RegexUnitPerceiver, SimpleUnitPerceiver]
        perceivers = list(map(lambda cls: cls(), perceiver_types))
        logger.debug(f"Created {len(perceivers)} perceivers")
        return perceivers

