#!/usr/bin/env python3
"""
Unit Converter Pipeline Controller - Functional approach with predicates.

Implements the complete pipeline using functional composition:
perceive → plan → reason → act → review → learn
"""

import asyncio
import logging
from itertools import chain
from typing import List, Dict, Any
from functools import partial, reduce

from pipeline_executor.framework.base_controller import BasePipelineController
from pipeline_executor.framework.models import PipelineContext, PipelineResult, RetryConfig
from pipeline_executor.framework.decorators import timing, error_boundary, memory_managed
from pipeline_executor.framework.utils import MemoryManager
from pipeline_executor.framework.colored_logging import EmojiLogger
from pipeline_executor.application.actor import Actor
from pipeline_executor.application.reviewer import Reviewer, Learner
from .unit_factories import UnitToolFactory, UnitPerceiverFactory
from .unit_planner import UnitPlanner
from .unit_reasoner import UnitReasoner

logger = EmojiLogger(__name__)


class UnitConverterController(BasePipelineController):
    """Async pipeline controller using functional programming patterns."""
    
    def __init__(self, 
                 timeout: int = 5, 
                 debug: bool = False,
                 perceiver_factory: UnitPerceiverFactory = None,
                 tool_factory: UnitToolFactory = None,
                 retry_config: RetryConfig = None):
        """Initialize controller with functional component composition."""
        super().__init__(timeout, debug)
        
        self._perceiver_factory = perceiver_factory or UnitPerceiverFactory()
        self._tool_factory = tool_factory or UnitToolFactory()
        self._retry_config = retry_config or RetryConfig()
        self._memory_manager = MemoryManager()
        
        self._components = self._create_components()
        
        logger.logger.info("🚀 UnitConverterController initialized with all components")
    
    def _create_components(self) -> Dict[str, Any]:
        """Factory method using functional composition."""
        component_creators = {
            'perceivers': lambda: self._perceiver_factory.create_perceivers(),
            'planner': lambda: UnitPlanner(self._tool_factory),
            'reasoner': lambda: UnitReasoner(self._retry_config),
            'actor': lambda: Actor(self._memory_manager),
            'reviewer': lambda: Reviewer(),
            'learner': lambda: Learner()
        }
        
        components = {k: creator() for k, creator in component_creators.items()}
        logger.logger.debug(f"🔧 Created {len(components)} pipeline components")
        return components
    
    @timing("perceive_stage")
    @error_boundary()
    async def _perceive_stage(self, context: PipelineContext) -> PipelineContext:
        """Perceive stage using functional composition."""
        logger.perceive_start(context.input_data)
        
        # Functional pipeline: concurrent perception → flatten → filter valid → deduplicate
        perception_tasks = list(map(
            lambda perceiver: asyncio.create_task(self._run_perceiver(perceiver, context.input_data)),
            self._components['perceivers']
        ))
        
        perception_results = await asyncio.gather(*perception_tasks)
        all_conversions = list(chain.from_iterable(perception_results))
        
        # Predicate-based filtering
        is_valid = lambda conv: conv.is_valid
        valid_conversions = list(filter(is_valid, all_conversions))
        invalid_conversions = list(filter(lambda conv: not is_valid(conv), all_conversions))
        
        # Functional deduplication
        deduplicated = self._deduplicate_conversions(valid_conversions)
        
        logger.perceive_complete(len(deduplicated), len(invalid_conversions))
        
        # Log invalid conversions using functional approach
        log_invalid = lambda conv: logger.logger.warning(f"⚠️ Invalid conversion: {conv.original} - {conv.error_message}")
        _ = context.debug and list(map(log_invalid, invalid_conversions))
        
        # Update context functionally
        return self._update_context_perceive(context, deduplicated, invalid_conversions)
    
    def _deduplicate_conversions(self, conversions):
        """Deduplicate using functional reduce."""
        def accumulate_unique(acc, conv):
            seen, unique = acc
            return (seen | {conv.original}, unique + [conv]) if conv.original not in seen else acc
        
        _, deduplicated = reduce(accumulate_unique, conversions, (set(), []))
        return deduplicated
    
    def _update_context_perceive(self, context, valid, invalid):
        """Update context using functional approach."""
        updates = {
            'stage_results': {
                **context.stage_results,
                'perceive': valid,
                'invalid_conversions': invalid
            },
            'metrics': {
                **context.metrics,
                'valid_conversions': len(valid),
                'invalid_conversions': len(invalid)
            }
        }
        
        context.stage_results.update(updates['stage_results'])
        context.metrics.update(updates['metrics'])
        return context
    
    async def _run_perceiver(self, perceiver, input_data):
        """Run perceiver asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, perceiver.perceive, input_data)
    
    @timing("plan_stage")
    @memory_managed(max_memory_mb=20)
    async def _plan_stage(self, context: PipelineContext) -> PipelineContext:
        """Plan stage using functional composition."""
        conversions = context.stage_results['perceive']
        
        # Predicate check
        has_conversions = lambda: len(conversions) > 0
        
        _ = has_conversions() or logger.logger.warning("⚠️ No valid conversions to plan")
        callables = await self._execute_planning(conversions) if has_conversions() else []
        
        logger.plan_complete(len(callables))
        
        return self._update_context_plan(context, callables)
    
    async def _execute_planning(self, conversions):
        """Execute planning asynchronously."""
        logger.plan_start(len(conversions))
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._components['planner'].plan, conversions)
    
    def _update_context_plan(self, context, callables):
        """Update context for plan stage."""
        context.stage_results['plan'] = callables
        context.metrics['planned_callables'] = len(callables)
        return context
    
    @timing("reason_stage")
    async def _reason_stage(self, context: PipelineContext) -> PipelineContext:
        """Reason stage using functional approach."""
        callables = context.stage_results['plan']
        
        has_callables = lambda: len(callables) > 0
        
        _ = has_callables() or logger.logger.warning("⚠️ No callables to reason about")
        strategy = await self._execute_reasoning(callables, context.timeout) if has_callables() else None
        
        _ = strategy and logger.reason_complete(strategy.total_workers)
        
        return self._update_context_reason(context, strategy)
    
    async def _execute_reasoning(self, callables, timeout):
        """Execute reasoning asynchronously."""
        logger.reason_start(len(callables), timeout)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._components['reasoner'].reason, callables, timeout)
    
    def _update_context_reason(self, context, strategy):
        """Update context for reason stage."""
        context.stage_results['reason'] = strategy
        
        updates = {
            'total_workers': strategy.total_workers if strategy else 0,
            'executor_configs': len(strategy.executor_configs) if strategy else 0
        }
        context.metrics.update(updates)
        return context
    
    @timing("act_stage")
    @memory_managed(max_memory_mb=50)
    async def _act_stage(self, context: PipelineContext) -> PipelineContext:
        """Act stage using functional execution."""
        strategy = context.stage_results['reason']
        
        has_strategy = lambda: strategy is not None
        
        _ = has_strategy() or logger.logger.warning("⚠️ No execution strategy available")
        results = await self._execute_strategy_safe(strategy, context.timeout) if has_strategy() else []
        
        logger.act_complete(len(results))
        
        return self._update_context_act(context, results)
    
    async def _execute_strategy_safe(self, strategy, timeout):
        """Execute strategy with timeout protection."""
        logger.act_start(strategy.total_workers, timeout)
        
        try:
            return await asyncio.wait_for(self._execute_strategy(strategy), timeout=timeout)
        except asyncio.TimeoutError:
            logger.timeout_warning("conversion execution", timeout)
            return []
    
    async def _execute_strategy(self, strategy):
        """Execute strategy using thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._components['actor'].act, strategy)
    
    def _update_context_act(self, context, results):
        """Update context for act stage."""
        context.stage_results['act'] = results
        context.metrics['execution_results'] = len(results)
        
        memory_usage = self._components['actor'].get_memory_usage()
        context.metrics.update(memory_usage)
        return context
    
    @timing("review_stage")
    async def _review_stage(self, context: PipelineContext) -> PipelineContext:
        """Review stage using functional composition."""
        logger.logger.debug("🔍 Starting review stage")
        
        results = context.stage_results['act']
        summary = await self._execute_review(results)
        
        success_rate = self._calculate_success_rate(summary)
        logger.review_complete(success_rate, summary.average_execution_time)
        
        return self._update_context_review(context, summary, success_rate)
    
    async def _execute_review(self, results):
        """Execute review asynchronously."""
        has_results = lambda: len(results) > 0
        
        if has_results():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._components['reviewer'].review, results)
        else:
            logger.logger.warning("⚠️ No results to review")
            from pipeline_executor.framework.models import ReviewSummary
            return ReviewSummary(
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                average_execution_time=0.0,
                results=[]
            )
    
    def _calculate_success_rate(self, summary):
        """Calculate success rate using functional approach."""
        has_operations = lambda: summary.total_operations > 0
        return (summary.successful_operations / summary.total_operations * 100) if has_operations() else 0
    
    def _update_context_review(self, context, summary, success_rate):
        """Update context for review stage."""
        context.stage_results['review'] = summary
        context.metrics.update({
            'success_rate': success_rate,
            'average_execution_time': summary.average_execution_time
        })
        return context
    
    @timing("learn_stage")
    async def _learn_stage(self, context: PipelineContext) -> PipelineContext:
        """Learn stage using functional composition."""
        logger.logger.debug("🔍 Starting learn stage")
        
        summary = context.stage_results['review']
        insights = await self._execute_learning(summary)
        
        logger.learn_complete(insights.success_rate, len(insights.performance_recommendations))
        
        # Functional logging of recommendations
        log_recommendations = lambda recs: list(map(
            lambda item: logger.logger.info(f"  {item[0]}. {item[1]}"),
            enumerate(recs, 1)
        ))
        
        has_recommendations = lambda: context.debug and insights.performance_recommendations
        _ = has_recommendations() and (
            logger.logger.info("💡 Performance recommendations:"),
            log_recommendations(insights.performance_recommendations)
        )
        
        return self._update_context_learn(context, insights)
    
    async def _execute_learning(self, summary):
        """Execute learning asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._components['learner'].learn, summary)
    
    def _update_context_learn(self, context, insights):
        """Update context for learn stage."""
        context.stage_results['learn'] = insights
        context.result = PipelineResult(summary=context.stage_results['review'], insights=insights)
        context.metrics['total_historical_executions'] = insights.total_executions
        return context
    
    async def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get metrics using functional composition."""
        loop = asyncio.get_event_loop()
        memory_usage = await loop.run_in_executor(None, self._memory_manager.get_memory_usage)
        
        return {
            'memory_usage': memory_usage,
            'component_count': len(self._components),
            'timeout': self.timeout,
            'debug_mode': self.debug
        }
    
    async def cleanup(self):
        """Clean up pipeline resources asynchronously."""
        logger.cleanup_start()
        
        loop = asyncio.get_event_loop()
        cleanup_tasks = [
            loop.run_in_executor(None, self._memory_manager.cleanup),
            loop.run_in_executor(None, self._tool_factory.clear_cache)
            if hasattr(self._tool_factory, 'clear_cache') else asyncio.sleep(0)
        ]
        
        await asyncio.gather(*cleanup_tasks)
        logger.cleanup_complete()
