"""
Data models for unit converter pipeline - Functional approach.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from functools import partial


class UnitCategory(Enum):
    """Supported unit categories for conversion."""
    LENGTH = "length"
    WEIGHT = "weight"
    TEMPERATURE = "temperature"
    VOLUME = "volume"
    TIME = "time"
    SPEED = "speed"
    UNKNOWN = "unknown"


# Predicate functions for unit categories
is_length = lambda category: category == UnitCategory.LENGTH
is_weight = lambda category: category == UnitCategory.WEIGHT
is_temperature = lambda category: category == UnitCategory.TEMPERATURE
is_volume = lambda category: category == UnitCategory.VOLUME
is_time = lambda category: category == UnitCategory.TIME
is_speed = lambda category: category == UnitCategory.SPEED
is_unknown = lambda category: category == UnitCategory.UNKNOWN


@dataclass
class UnitConversion:
    """
    Represents a unit conversion request.
    
    Uses functional predicates for validation.
    """
    original: str
    value: float = 0.0
    from_unit: str = ""
    to_unit: str = ""
    category: UnitCategory = UnitCategory.UNKNOWN
    is_valid: bool = False
    error_message: Optional[str] = None
    
    def __repr__(self):
        format_valid = lambda: f"UnitConversion('{self.original}': {self.value} {self.from_unit} → {self.to_unit} [{self.category.value}])"
        format_invalid = lambda: f"UnitConversion('{self.original}': INVALID - {self.error_message})"
        return format_valid() if self.is_valid else format_invalid()
    
    def __hash__(self):
        return hash(self.original)


# Factory functions using functional approach
create_valid_conversion = lambda original, value, from_unit, to_unit, category: UnitConversion(
    original=original,
    value=value,
    from_unit=from_unit,
    to_unit=to_unit,
    category=category,
    is_valid=True
)

create_invalid_conversion = lambda original, error_msg: UnitConversion(
    original=original,
    is_valid=False,
    error_message=error_msg
)
