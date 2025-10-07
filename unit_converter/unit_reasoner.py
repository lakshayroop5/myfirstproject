"""Reasoner using functional worker allocation."""

import logging
from typing import List, Tuple
from functools import partial
from pipeline_executor.framework.models import ExecutionStrategy, ExecutorConfig, RetryConfig

logger = logging.getLogger(__name__)


class UnitReasoner:
    """Determines execution strategy using functional approach."""
    
    def __init__(self, retry_config: RetryConfig = None):
        """Initialize reasoner with functional configuration."""
        self._retry_config = retry_config or RetryConfig()
        
        # Functional worker calculation predicates
        self._worker_strategies = [
            (lambda n: n == 0, lambda n: 1),
            (lambda n: n <= 5, lambda n: n),
            (lambda n: n <= 20, lambda n: min(10, n)),
            (lambda n: True, lambda n: 20)  # Default case
        ]
        
        logger.debug("UnitReasoner initialized")
    
    def reason(self, callables: List[Tuple], timeout: int) -> ExecutionStrategy:
        """Determine execution strategy using functional reasoning."""
        num_conversions = len(callables)
        logger.debug(f"Reasoning about execution strategy for {num_conversions} conversions")
        
        # Functional worker calculation
        num_workers = self._calculate_workers(num_conversions)
        per_conversion_timeout = self._calculate_timeout(num_conversions, num_workers, timeout)
        
        # Create configuration using functional composition
        executor_config = ExecutorConfig(
            max_workers=num_workers,
            timeout_per_task=per_conversion_timeout,
            retry_config=self._retry_config
        )
        
        strategy = ExecutionStrategy(
            total_workers=num_workers,
            executor_configs=[executor_config],
            callables=callables
        )
        
        logger.debug(f"Strategy: {num_workers} workers, {per_conversion_timeout:.2f}s per task")
        return strategy
    
    def _calculate_workers(self, task_count: int) -> int:
        """Calculate workers using functional pattern matching."""
        # Find first matching strategy
        matched = list(filter(lambda s: s[0](task_count), self._worker_strategies))
        return matched[0][1](task_count) if matched else 1
    
    def _calculate_timeout(self, num_conversions: int, num_workers: int, total_timeout: int) -> float:
        """Calculate per-conversion timeout functionally."""
        overhead_time = 1
        available_time = max(1, total_timeout - overhead_time)
        divisor = max(1, num_conversions / num_workers)
        return available_time / divisor
