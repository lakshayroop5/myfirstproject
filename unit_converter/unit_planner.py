"""Planner using functional composition and command pattern."""

import logging
from typing import List, Callable, Tuple
from functools import partial
from .unit_models import UnitConversion
from .unit_routing import UnitRouter

logger = logging.getLogger(__name__)


class UnitPlanner:
    """Plans execution using functional composition."""
    
    def __init__(self, tool_factory):
        """Initialize planner with functional components."""
        self._tool_factory = tool_factory
        self._router = UnitRouter(tool_factory)
        logger.debug("UnitPlanner initialized")
    
    def plan(self, conversions: List[UnitConversion]) -> List[Tuple[UnitConversion, Callable]]:
        """Create execution plan using functional pipeline."""
        logger.debug(f"Planning execution for {len(conversions)} conversions")
        
        # Functional pipeline: filter valid → map to callable → filter None
        is_valid = lambda conv: conv.is_valid
        to_callable = lambda conv: (conv, self._create_callable_for(conv))
        is_not_none = lambda item: item[1] is not None
        
        callables = list(filter(
            is_not_none,
            map(to_callable, filter(is_valid, conversions))
        ))
        
        logger.debug(f"Created {len(callables)} executable plans")
        return callables
    
    def _create_callable_for(self, conversion: UnitConversion):
        """Create callable using functional approach."""
        try:
            tool = self._router.route(conversion)
            return self._build_executable(conversion, tool) if tool else None
        except Exception as e:
            logger.error(f"Error planning conversion {conversion}: {e}")
            return None
    
    def _build_executable(self, conversion: UnitConversion, tool) -> Callable:
        """Build executable using functional closure."""
        create_success = lambda result: {
            'conversion': conversion.original,
            'input': f"{conversion.value} {conversion.from_unit}",
            'output': f"{result} {conversion.to_unit}",
            'result': result,
            'category': conversion.category.value,
            'success': True,
            'error': None
        }
        
        create_failure = lambda error: {
            'conversion': conversion.original,
            'input': f"{conversion.value} {conversion.from_unit}",
            'output': None,
            'result': None,
            'category': conversion.category.value,
            'success': False,
            'error': str(error)
        }
        
        def execute_conversion():
            """Execute conversion with functional error handling."""
            try:
                result = tool.execute(
                    value=conversion.value,
                    from_unit=conversion.from_unit,
                    to_unit=conversion.to_unit
                )
                return create_success(result)
            except Exception as e:
                logger.error(f"Conversion failed: {conversion.original} - {e}")
                return create_failure(e)
        
        return execute_conversion
