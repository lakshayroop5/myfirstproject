"""Unit conversion tools - Functional approach with predicates."""

import logging
from typing import Dict, Callable
from functools import partial
from pipeline_executor.framework.decorators import retry, timing, memory_managed, error_boundary

logger = logging.getLogger(__name__)


# Functional utility for unit conversion
def create_converter(to_base_factors: Dict[str, float]):
    """Higher-order function to create unit converters."""
    normalize = lambda unit: unit.lower()
    
    def convert(value: float, from_unit: str, to_unit: str) -> float:
        from_normalized, to_normalized = normalize(from_unit), normalize(to_unit)
        
        # Predicate validation
        is_valid_unit = lambda unit: unit in to_base_factors
        validate = lambda units: all(map(is_valid_unit, units))
        
        # Raise errors functionally
        _ = validate([from_normalized, to_normalized]) or (
            lambda: (_ for _ in ()).throw(ValueError(f"Unknown units: {from_unit} or {to_unit}"))
        )()
        
        # Convert through base unit
        base_value = value * to_base_factors[from_normalized]
        return base_value / to_base_factors[to_normalized]
    
    return convert


class LengthTool:
    """Length conversions using functional approach."""
    
    def __init__(self):
        self._to_meters = {
            'meter': 1.0, 'meters': 1.0, 'm': 1.0,
            'kilometer': 1000.0, 'kilometers': 1000.0, 'km': 1000.0,
            'centimeter': 0.01, 'centimeters': 0.01, 'cm': 0.01,
            'millimeter': 0.001, 'millimeters': 0.001, 'mm': 0.001,
            'mile': 1609.34, 'miles': 1609.34,
            'yard': 0.9144, 'yards': 0.9144,
            'foot': 0.3048, 'feet': 0.3048, 'ft': 0.3048,
            'inch': 0.0254, 'inches': 0.0254, 'in': 0.0254
        }
        self._convert = create_converter(self._to_meters)
        logger.debug("LengthTool initialized")
    
    @retry(max_attempts=2)
    @timing("length_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional converter."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        result = self._convert(value, from_unit, to_unit)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result


class WeightTool:
    """Weight conversions using functional approach."""
    
    def __init__(self):
        self._to_kg = {
            'kilogram': 1.0, 'kilograms': 1.0, 'kg': 1.0,
            'gram': 0.001, 'grams': 0.001, 'g': 0.001,
            'milligram': 0.000001, 'milligrams': 0.000001, 'mg': 0.000001,
            'pound': 0.453592, 'pounds': 0.453592, 'lb': 0.453592, 'lbs': 0.453592,
            'ounce': 0.0283495, 'ounces': 0.0283495, 'oz': 0.0283495,
            'ton': 1000.0, 'tons': 1000.0, 'tonne': 1000.0, 'tonnes': 1000.0
        }
        self._convert = create_converter(self._to_kg)
        logger.debug("WeightTool initialized")
    
    @retry(max_attempts=2)
    @timing("weight_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional converter."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        result = self._convert(value, from_unit, to_unit)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result


class TemperatureTool:
    """Temperature conversions using functional dispatch."""
    
    def __init__(self):
        # Functional dispatch table
        self._conversions = {
            ('celsius', 'fahrenheit'): lambda c: (c * 9/5) + 32,
            ('fahrenheit', 'celsius'): lambda f: (f - 32) * 5/9,
            ('celsius', 'kelvin'): lambda c: c + 273.15,
            ('kelvin', 'celsius'): lambda k: k - 273.15,
            ('fahrenheit', 'kelvin'): lambda f: (f - 32) * 5/9 + 273.15,
            ('kelvin', 'fahrenheit'): lambda k: (k - 273.15) * 9/5 + 32
        }
        logger.debug("TemperatureTool initialized")
    
    @retry(max_attempts=2)
    @timing("temperature_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional dispatch."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        
        from_normalized, to_normalized = from_unit.lower(), to_unit.lower()
        
        # Same unit predicate
        is_same_unit = lambda: from_normalized == to_normalized
        
        # Get conversion function
        conversion_key = (from_normalized, to_normalized)
        converter = self._conversions.get(conversion_key)
        
        # Functional error handling
        _ = converter or (lambda: (_ for _ in ()).throw(
            ValueError(f"Cannot convert from {from_unit} to {to_unit}")
        ))()
        
        result = value if is_same_unit() else converter(value)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result


class VolumeTool:
    """Volume conversions using functional approach."""
    
    def __init__(self):
        self._to_liters = {
            'liter': 1.0, 'liters': 1.0, 'l': 1.0,
            'milliliter': 0.001, 'milliliters': 0.001, 'ml': 0.001,
            'gallon': 3.78541, 'gallons': 3.78541, 'gal': 3.78541,
            'quart': 0.946353, 'quarts': 0.946353, 'qt': 0.946353,
            'pint': 0.473176, 'pints': 0.473176, 'pt': 0.473176,
            'cup': 0.236588, 'cups': 0.236588,
            'tablespoon': 0.0147868, 'tablespoons': 0.0147868, 'tbsp': 0.0147868,
            'teaspoon': 0.00492892, 'teaspoons': 0.00492892, 'tsp': 0.00492892
        }
        self._convert = create_converter(self._to_liters)
        logger.debug("VolumeTool initialized")
    
    @retry(max_attempts=2)
    @timing("volume_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional converter."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        result = self._convert(value, from_unit, to_unit)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result


class TimeTool:
    """Time conversions using functional approach."""
    
    def __init__(self):
        self._to_seconds = {
            'second': 1.0, 'seconds': 1.0, 's': 1.0, 'sec': 1.0,
            'minute': 60.0, 'minutes': 60.0, 'min': 60.0,
            'hour': 3600.0, 'hours': 3600.0, 'hr': 3600.0,
            'day': 86400.0, 'days': 86400.0,
            'week': 604800.0, 'weeks': 604800.0,
            'month': 2592000.0, 'months': 2592000.0,
            'year': 31536000.0, 'years': 31536000.0
        }
        self._convert = create_converter(self._to_seconds)
        logger.debug("TimeTool initialized")
    
    @retry(max_attempts=2)
    @timing("time_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional converter."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        result = self._convert(value, from_unit, to_unit)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result


class SpeedTool:
    """Speed conversions using functional approach."""
    
    def __init__(self):
        self._to_mps = {
            'm/s': 1.0, 'mps': 1.0, 'meters/second': 1.0,
            'km/h': 0.277778, 'kmh': 0.277778, 'kph': 0.277778, 'kilometers/hour': 0.277778,
            'mph': 0.44704, 'miles/hour': 0.44704,
            'knot': 0.514444, 'knots': 0.514444,
            'ft/s': 0.3048, 'fps': 0.3048, 'feet/second': 0.3048
        }
        self._convert = create_converter(self._to_mps)
        logger.debug("SpeedTool initialized")
    
    @retry(max_attempts=2)
    @timing("speed_conversion")
    @memory_managed(max_memory_mb=5)
    @error_boundary()
    def execute(self, value: float, from_unit: str, to_unit: str) -> float:
        """Execute conversion using functional converter."""
        logger.debug(f"Converting {value} {from_unit} to {to_unit}")
        result = self._convert(value, from_unit, to_unit)
        logger.debug(f"Conversion result: {result} {to_unit}")
        return result
