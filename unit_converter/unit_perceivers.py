"""
Perceivers for parsing unit conversion requests - Functional approach.
"""

import re
import logging
from typing import List
from functools import reduce, partial
from itertools import chain
from .unit_models import UnitConversion, UnitCategory, create_valid_conversion, create_invalid_conversion

logger = logging.getLogger(__name__)


class UnitCategoryDetector:
    """Helper class to detect unit categories using predicates."""
    
    LENGTH_UNITS = {
        'meter', 'meters', 'm', 'kilometer', 'kilometers', 'km',
        'centimeter', 'centimeters', 'cm', 'millimeter', 'millimeters', 'mm',
        'mile', 'miles', 'yard', 'yards', 'foot', 'feet', 'ft',
        'inch', 'inches', 'in'
    }
    
    WEIGHT_UNITS = {
        'kilogram', 'kilograms', 'kg', 'gram', 'grams', 'g',
        'milligram', 'milligrams', 'mg', 'pound', 'pounds', 'lb', 'lbs',
        'ounce', 'ounces', 'oz', 'ton', 'tons', 'tonne', 'tonnes'
    }
    
    TEMPERATURE_UNITS = {'celsius', 'fahrenheit', 'kelvin', 'c', 'f', 'k'}
    
    VOLUME_UNITS = {
        'liter', 'liters', 'l', 'milliliter', 'milliliters', 'ml',
        'gallon', 'gallons', 'gal', 'quart', 'quarts', 'qt',
        'pint', 'pints', 'pt', 'cup', 'cups',
        'tablespoon', 'tablespoons', 'tbsp', 'teaspoon', 'teaspoons', 'tsp'
    }
    
    TIME_UNITS = {
        'second', 'seconds', 's', 'sec', 'minute', 'minutes', 'min',
        'hour', 'hours', 'hr', 'day', 'days',
        'week', 'weeks', 'month', 'months', 'year', 'years'
    }
    
    SPEED_UNITS = {
        'm/s', 'mps', 'meters/second', 'km/h', 'kmh', 'kph', 'kilometers/hour',
        'mph', 'miles/hour', 'knot', 'knots', 'ft/s', 'fps', 'feet/second'
    }
    
    # Predicate functions for category detection
    @staticmethod
    def is_both_in_set(unit_set, from_unit, to_unit):
        return from_unit.lower() in unit_set and to_unit.lower() in unit_set
    
    @classmethod
    def detect_category(cls, from_unit: str, to_unit: str) -> UnitCategory:
        """Detect category using functional dispatch."""
        check_in_set = partial(cls.is_both_in_set, from_unit=from_unit, to_unit=to_unit)
        
        category_mappings = [
            (partial(cls.is_both_in_set, cls.LENGTH_UNITS), UnitCategory.LENGTH),
            (partial(cls.is_both_in_set, cls.WEIGHT_UNITS), UnitCategory.WEIGHT),
            (partial(cls.is_both_in_set, cls.TEMPERATURE_UNITS), UnitCategory.TEMPERATURE),
            (partial(cls.is_both_in_set, cls.VOLUME_UNITS), UnitCategory.VOLUME),
            (partial(cls.is_both_in_set, cls.TIME_UNITS), UnitCategory.TIME),
            (partial(cls.is_both_in_set, cls.SPEED_UNITS), UnitCategory.SPEED),
        ]
        
        # Functional pattern matching
        matched = list(filter(lambda mapping: mapping[0](from_unit, to_unit), category_mappings))
        return matched[0][1] if matched else UnitCategory.UNKNOWN


class RegexUnitPerceiver:
    """Perceiver using regex patterns - Functional approach."""
    
    def __init__(self):
        self.patterns = [
            re.compile(r'([0-9]*\.?[0-9]+)\s+([a-zA-Z/]+)\s+to\s+([a-zA-Z/]+)', re.IGNORECASE),
            re.compile(r'convert\s+([0-9]*\.?[0-9]+)\s+([a-zA-Z/]+)\s+to\s+([a-zA-Z/]+)', re.IGNORECASE),
            re.compile(r'([0-9]*\.?[0-9]+)\s*([a-zA-Z/]+)\s+to\s+([a-zA-Z/]+)', re.IGNORECASE),
            re.compile(r'([0-9]*\.?[0-9]+)\s+([a-zA-Z/]+)\s*->\s*([a-zA-Z/]+)', re.IGNORECASE),
        ]
        logger.debug(f"RegexUnitPerceiver initialized with {len(self.patterns)} patterns")
    
    def perceive(self, input_text: str) -> List[UnitConversion]:
        """Parse conversions using functional approach."""
        logger.debug(f"Perceiving conversions from: {input_text}")
        
        # Functional pipeline: split → filter empty → parse → flatten
        segments = list(filter(lambda s: s, map(str.strip, input_text.split(','))))
        conversions = list(map(self._parse_segment, segments))
        
        logger.debug(f"Perceived {len(conversions)} conversions from input")
        return conversions
    
    def _parse_segment(self, segment: str) -> UnitConversion:
        """Parse segment using functional pattern matching."""
        # Try all patterns and return first match
        parse_attempts = list(map(lambda pattern: self._try_pattern(pattern, segment), self.patterns))
        valid_parses = list(filter(lambda conv: conv is not None, parse_attempts))
        
        return valid_parses[0] if valid_parses else create_invalid_conversion(
            segment, "Could not parse conversion format"
        )
    
    def _try_pattern(self, pattern, segment: str):
        """Try to parse with a specific pattern."""
        match = pattern.search(segment)
        return self._create_from_match(match, segment) if match else None
    
    def _create_from_match(self, match, segment: str):
        """Create conversion from regex match using functional approach."""
        try:
            value, from_unit, to_unit = float(match.group(1)), match.group(2).strip(), match.group(3).strip()
            category = UnitCategoryDetector.detect_category(from_unit, to_unit)
            
            # Predicate-based validation
            is_unknown = lambda cat: cat == UnitCategory.UNKNOWN
            return create_invalid_conversion(
                segment, f"Unknown or mismatched unit types: {from_unit} and {to_unit}"
            ) if is_unknown(category) else create_valid_conversion(
                segment, value, from_unit, to_unit, category
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing segment '{segment}': {e}")
            return create_invalid_conversion(segment, f"Parse error: {str(e)}")


class SimpleUnitPerceiver:
    """Simple perceiver for basic formats - Functional approach."""
    
    def perceive(self, input_text: str) -> List[UnitConversion]:
        """Parse simple conversion formats functionally."""
        logger.debug(f"SimplePerceiver processing: {input_text}")
        
        # Functional pipeline: split → filter valid → map parse → filter successful
        segments = list(filter(
            lambda s: s and 'to' in s.lower(),
            map(str.strip, input_text.split(','))
        ))
        
        conversions = list(filter(
            lambda conv: conv is not None,
            map(self._try_parse_segment, segments)
        ))
        
        return conversions
    
    def _try_parse_segment(self, segment: str):
        """Try to parse a segment, returning None on failure."""
        try:
            parts = segment.lower().split('to')
            left_parts = parts[0].strip().split() if len(parts) == 2 else []
            
            # Predicate validation
            has_sufficient_parts = lambda parts: len(parts) >= 2
            return self._create_conversion(segment, left_parts, parts[1].strip()) if (
                has_sufficient_parts(left_parts)
            ) else None
            
        except (ValueError, IndexError):
            return None
    
    def _create_conversion(self, segment, left_parts, to_unit):
        """Create conversion from parsed parts."""
        value = float(left_parts[0])
        from_unit = ' '.join(left_parts[1:]).strip()
        category = UnitCategoryDetector.detect_category(from_unit, to_unit)
        
        is_valid_category = lambda cat: cat != UnitCategory.UNKNOWN
        return create_valid_conversion(
            segment, value, from_unit, to_unit, category
        ) if is_valid_category(category) else None
