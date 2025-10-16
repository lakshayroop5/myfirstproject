"""Core spine implementation for agentic workflows."""

import asyncio
import uuid
from typing import Callable, List, Dict, Any, Optional, Iterable, Union
from functools import reduce

from prefect import task, flow
from prefect.futures import PrefectFuture
from prefect.cache_policies import NONE as NO_CACHE

from .stages import Stage
from .context import Context, merge_context
from .state import get_state_manager, stage_execution_context, StageState, StageExecution
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _collect_functions(functions: List[Callable]) -> Dict[Stage, List[Callable]]:
    """Collect functions by their stage type."""
    stage_map: Dict[Stage, List[Callable]] = {}
    
    for fn in functions:
        stage = getattr(fn, "_agent_stage", None)
        if stage is not None:
            stage_map.setdefault(stage, []).append(fn)
        else:
            logger.warning(f"Function {fn.__name__} has no stage decorator")
    
    return stage_map


def _wrap_as_task(fn: Callable) -> Callable:
    """Wrap function as Prefect task if not already a task."""
    # If it's already a task, get the original function
    if hasattr(fn, 'fn'):
        original_fn = fn.fn
        task_name = getattr(fn, 'name', getattr(original_fn, "__name__", "stage"))
    else:
        original_fn = fn
        task_name = getattr(fn, "__name__", "stage")
    
    return task(
        name=task_name,
        cache_policy=NO_CACHE  # Disable caching to avoid serialization issues
    )(original_fn)


def _as_task(fn: Callable) -> Callable:
    """Convert function to Prefect task if needed."""
    # Check if already a Prefect task (has submit method)
    if hasattr(fn, "submit"):
        return fn
    else:
        return _wrap_as_task(fn)


def _merge_context_dict(ctx: Dict[str, Any], output: Any) -> Dict[str, Any]:
    """Merge output into context dictionary (for Prefect compatibility)."""
    if isinstance(output, dict):
        ctx.update(output)
        return ctx
    else:
        # Store non-dict outputs under a type-based key
        key = f"result_{output.__class__.__name__}"
        ctx[key] = output
        return ctx


def _execute_sequential(functions: List[Callable], ctx: Context) -> List[Any]:
    """Execute functions sequentially."""
    results = []
    for fn in functions:
        try:
            result = fn(ctx)
            results.append(result)
            logger.debug(f"Sequential execution of {fn.__name__} completed")
        except Exception as e:
            logger.error(f"Error in sequential execution of {fn.__name__}: {e}")
            raise
    return results


def _execute_sequential_prefect(tasks: List[Callable], ctx: Dict[str, Any]) -> List[Any]:
    """Execute Prefect tasks sequentially."""
    return [task.submit(ctx).result() for task in tasks]


def _execute_concurrent_prefect(tasks: List[Callable], ctx: Dict[str, Any]) -> List[Any]:
    """Execute Prefect tasks concurrently."""
    futures: List[PrefectFuture] = [task.submit(ctx) for task in tasks]
    return [future.result() for future in futures]


def _execute_sequential_prefect_monitored(tasks: List[Callable], ctx: Dict[str, Any], stage: Stage, workflow_id: str) -> List[Any]:
    """Execute Prefect tasks sequentially with state monitoring."""
    results = []
    state_manager = get_state_manager()
    
    for task in tasks:
        function_name = getattr(task, 'name', getattr(task, '__name__', 'unknown'))
        
        with stage_execution_context(stage, function_name, workflow_id) as execution:
            try:
                result = task.submit(ctx).result()
                execution.result = result
                results.append(result)
            except Exception as e:
                logger.error(f"Task {function_name} failed: {e}")
                raise
    
    return results


def _execute_concurrent_prefect_monitored(tasks: List[Callable], ctx: Dict[str, Any], stage: Stage, workflow_id: str) -> List[Any]:
    """Execute Prefect tasks concurrently with state monitoring."""
    state_manager = get_state_manager()
    executions = []
    
    # Create execution trackers for all tasks
    for task in tasks:
        function_name = getattr(task, 'name', getattr(task, '__name__', 'unknown'))
        execution = state_manager.create_execution(stage, function_name, workflow_id)
        executions.append(execution)
    
    try:
        # Mark all as started
        for execution in executions:
            state_manager.update_state(execution, StageState.STARTED)
            state_manager.update_state(execution, StageState.RUNNING)
        
        # Execute concurrently
        futures: List[PrefectFuture] = [task.submit(ctx) for task in tasks]
        results = [future.result() for future in futures]
        
        # Mark all as completed and store results
        for execution, result in zip(executions, results):
            execution.result = result
            state_manager.update_state(execution, StageState.COMPLETED, result=result)
        
        return results
        
    except Exception as e:
        # Mark any unfinished executions as error
        for execution in executions:
            if not execution.is_finished:
                state_manager.update_state(execution, StageState.ERROR, error=e)
        raise


async def _execute_concurrent(functions: List[Callable], ctx: Context) -> List[Any]:
    """Execute functions concurrently."""
    async def run_function(fn: Callable) -> Any:
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(ctx)
            else:
                result = fn(ctx)
            logger.debug(f"Concurrent execution of {fn.__name__} completed")
            return result
        except Exception as e:
            logger.error(f"Error in concurrent execution of {fn.__name__}: {e}")
            raise
    
    tasks = [run_function(fn) for fn in functions]
    return await asyncio.gather(*tasks)


def _execute_stage_sync(
    functions: List[Callable], 
    ctx: Context, 
    concurrent: bool = False
) -> Context:
    """Execute a stage synchronously."""
    if not functions:
        return ctx
    
    if concurrent:
        logger.warning("Concurrent execution requested in sync mode, falling back to sequential")
    
    results = _execute_sequential(functions, ctx)
    
    # Apply results sequentially to avoid issues
    current_ctx = ctx
    for result in results:
        current_ctx = merge_context(current_ctx, result)
    
    return current_ctx


def _execute_stage_sync_monitored(
    functions: List[Callable], 
    ctx: Context, 
    concurrent: bool = False,
    stage: Stage = None,
    workflow_id: str = "default"
) -> Context:
    """Execute a stage synchronously with state monitoring."""
    if not functions:
        return ctx
    
    if concurrent:
        logger.warning("Concurrent execution requested in sync mode, falling back to sequential")
    
    results = _execute_sequential_monitored(functions, ctx, stage, workflow_id)
    
    # Apply results sequentially to avoid issues
    current_ctx = ctx
    for result in results:
        current_ctx = merge_context(current_ctx, result)
    
    return current_ctx


def _execute_sequential_monitored(functions: List[Callable], ctx: Context, stage: Stage, workflow_id: str) -> List[Any]:
    """Execute functions sequentially with state monitoring."""
    results = []
    state_manager = get_state_manager()
    
    for fn in functions:
        function_name = getattr(fn, '__name__', 'unknown')
        
        with stage_execution_context(stage, function_name, workflow_id) as execution:
            try:
                if asyncio.iscoroutinefunction(fn):
                    logger.warning(f"Async function {function_name} called in sync context")
                    result = fn(ctx)  # This will return a coroutine, which is not ideal
                else:
                    result = fn(ctx)
                
                execution.result = result
                results.append(result)
                logger.debug(f"Sequential execution of {function_name} completed")
                
            except Exception as e:
                logger.error(f"Error in sequential execution of {function_name}: {e}")
                raise
    
    return results


async def _execute_stage_async(
    functions: List[Callable], 
    ctx: Context, 
    concurrent: bool = False
) -> Context:
    """Execute a stage asynchronously."""
    if not functions:
        return ctx
    
    if concurrent:
        results = await _execute_concurrent(functions, ctx)
    else:
        results = []
        for fn in functions:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(ctx)
            else:
                result = fn(ctx)
            results.append(result)
    
    # Apply results sequentially to avoid deepcopy issues
    current_ctx = ctx
    for result in results:
        current_ctx = merge_context(current_ctx, result)
    
    return current_ctx


async def _execute_stage_async_monitored(
    functions: List[Callable], 
    ctx: Context, 
    concurrent: bool = False,
    stage: Stage = None,
    workflow_id: str = "default"
) -> Context:
    """Execute a stage asynchronously with state monitoring."""
    if not functions:
        return ctx
    
    if concurrent:
        results = await _execute_concurrent_monitored(functions, ctx, stage, workflow_id)
    else:
        results = await _execute_sequential_async_monitored(functions, ctx, stage, workflow_id)
    
    # Apply results sequentially to avoid deepcopy issues
    current_ctx = ctx
    for result in results:
        current_ctx = merge_context(current_ctx, result)
    
    return current_ctx


async def _execute_sequential_async_monitored(functions: List[Callable], ctx: Context, stage: Stage, workflow_id: str) -> List[Any]:
    """Execute functions sequentially in async mode with state monitoring."""
    results = []
    state_manager = get_state_manager()
    
    for fn in functions:
        function_name = getattr(fn, '__name__', 'unknown')
        
        with stage_execution_context(stage, function_name, workflow_id) as execution:
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(ctx)
                else:
                    result = fn(ctx)
                
                execution.result = result
                results.append(result)
                logger.debug(f"Sequential async execution of {function_name} completed")
                
            except Exception as e:
                logger.error(f"Error in sequential async execution of {function_name}: {e}")
                raise
    
    return results


async def _execute_concurrent_monitored(functions: List[Callable], ctx: Context, stage: Stage, workflow_id: str) -> List[Any]:
    """Execute functions concurrently with state monitoring."""
    state_manager = get_state_manager()
    executions = []
    
    # Create execution trackers for all functions
    for fn in functions:
        function_name = getattr(fn, '__name__', 'unknown')
        execution = state_manager.create_execution(stage, function_name, workflow_id)
        executions.append(execution)
    
    async def run_function_monitored(fn: Callable, execution: StageExecution) -> Any:
        try:
            # Mark as started and running
            state_manager.update_state(execution, StageState.STARTED)
            state_manager.update_state(execution, StageState.RUNNING)
            
            if asyncio.iscoroutinefunction(fn):
                result = await fn(ctx)
            else:
                result = fn(ctx)
            
            # Mark as completed
            execution.result = result
            state_manager.update_state(execution, StageState.COMPLETED, result=result)
            logger.debug(f"Concurrent execution of {fn.__name__} completed")
            return result
            
        except Exception as e:
            # Mark as error
            state_manager.update_state(execution, StageState.ERROR, error=e)
            logger.error(f"Error in concurrent execution of {fn.__name__}: {e}")
            raise
    
    # Execute all functions concurrently
    tasks = [run_function_monitored(fn, execution) for fn, execution in zip(functions, executions)]
    return await asyncio.gather(*tasks)


@flow(name="AgenticSpine")
def agentic_spine(
    input_data: Any,
    functions: List[Callable],
    initial_context: Optional[Dict[str, Any]] = None,
    concurrent: Optional[Dict[Stage, bool]] = None,
    workflow_id: Optional[str] = None,
) -> Context:
    """
    Execute agentic workflow using Prefect flow.
    
    Args:
        input_data: Input data for the workflow
        functions: List of stage functions
        initial_context: Additional initial context
        concurrent: Stage-level concurrency settings
        workflow_id: Unique identifier for workflow monitoring
        
    Returns:
        Final context after all stages
    """
    # Generate workflow ID if not provided
    if workflow_id is None:
        workflow_id = f"prefect_sync_{uuid.uuid4().hex[:8]}"
    
    state_manager = get_state_manager()
    
    try:
        logger.info(f"Starting Prefect agentic spine execution - {workflow_id}")
        state_manager.start_workflow(workflow_id)
        
        # Initialize context as dict for Prefect compatibility
        ctx_dict = {"input": input_data, **(initial_context or {})}
        
        # Collect functions by stage
        stage_map = _collect_functions(functions)
        concurrent_settings = concurrent or {}
        
        # Execute stages in order using Prefect tasks
        stage_order = [Stage.PERCEIVE, Stage.REASON, Stage.PLAN, Stage.ACT]
        
        for stage in stage_order:
            stage_functions = stage_map.get(stage, [])
            if stage_functions:
                logger.info(f"Executing {stage.name} stage with {len(stage_functions)} functions")
                
                # Convert to Prefect tasks
                tasks = [_as_task(fn) for fn in stage_functions]
                
                # Choose execution strategy
                is_concurrent = concurrent_settings.get(stage, False)
                if is_concurrent:
                    results = _execute_concurrent_prefect_monitored(tasks, ctx_dict, stage, workflow_id)
                else:
                    results = _execute_sequential_prefect_monitored(tasks, ctx_dict, stage, workflow_id)
                
                # Merge results into context
                for result in results:
                    ctx_dict = _merge_context_dict(ctx_dict, result)
        
        logger.info(f"Prefect agentic spine execution completed - {workflow_id}")
        state_manager.complete_workflow(workflow_id)
        return Context(data=ctx_dict)
        
    except Exception as e:
        logger.error(f"Prefect agentic spine execution failed - {workflow_id}: {e}")
        state_manager.error_workflow(workflow_id, e)
        raise


def agentic_spine_simple(
    input_data: Any,
    functions: List[Callable],
    initial_context: Optional[Dict[str, Any]] = None,
    concurrent: Optional[Dict[Stage, bool]] = None,
    workflow_id: Optional[str] = None,
) -> Context:
    """
    Execute agentic workflow without Prefect (simple version).
    
    Args:
        input_data: Input data for the workflow
        functions: List of stage functions
        initial_context: Additional initial context
        concurrent: Stage-level concurrency settings
        workflow_id: Unique identifier for workflow monitoring
        
    Returns:
        Final context after all stages
    """
    # Generate workflow ID if not provided
    if workflow_id is None:
        workflow_id = f"simple_sync_{uuid.uuid4().hex[:8]}"
    
    state_manager = get_state_manager()
    
    try:
        logger.info(f"Starting simple agentic spine execution - {workflow_id}")
        state_manager.start_workflow(workflow_id)
        
        # Initialize context
        ctx_data = {"input": input_data, **(initial_context or {})}
        ctx = Context(data=ctx_data)
        
        # Collect functions by stage
        stage_map = _collect_functions(functions)
        concurrent_settings = concurrent or {}
        
        # Execute stages in order
        stage_order = [Stage.PERCEIVE, Stage.REASON, Stage.PLAN, Stage.ACT]
        
        for stage in stage_order:
            stage_functions = stage_map.get(stage, [])
            if stage_functions:
                logger.info(f"Executing {stage.name} stage with {len(stage_functions)} functions")
                is_concurrent = concurrent_settings.get(stage, False)
                ctx = _execute_stage_sync_monitored(stage_functions, ctx, is_concurrent, stage, workflow_id)
        
        logger.info(f"Simple agentic spine execution completed - {workflow_id}")
        state_manager.complete_workflow(workflow_id)
        return ctx
        
    except Exception as e:
        logger.error(f"Simple agentic spine execution failed - {workflow_id}: {e}")
        state_manager.error_workflow(workflow_id, e)
        raise


async def agentic_spine_async(
    input_data: Any,
    functions: List[Callable],
    initial_context: Optional[Dict[str, Any]] = None,
    concurrent: Optional[Dict[Stage, bool]] = None,
    workflow_id: Optional[str] = None,
) -> Context:
    """
    Execute agentic workflow asynchronously (simple version).
    
    Args:
        input_data: Input data for the workflow
        functions: List of stage functions
        initial_context: Additional initial context
        concurrent: Stage-level concurrency settings
        workflow_id: Unique identifier for workflow monitoring
        
    Returns:
        Final context after all stages
    """
    # Generate workflow ID if not provided
    if workflow_id is None:
        workflow_id = f"simple_async_{uuid.uuid4().hex[:8]}"
    
    state_manager = get_state_manager()
    
    try:
        logger.info(f"Starting asynchronous agentic spine execution - {workflow_id}")
        state_manager.start_workflow(workflow_id)
        
        # Initialize context
        ctx_data = {"input": input_data, **(initial_context or {})}
        ctx = Context(data=ctx_data)
        
        # Collect functions by stage
        stage_map = _collect_functions(functions)
        concurrent_settings = concurrent or {}
        
        # Execute stages in order
        stage_order = [Stage.PERCEIVE, Stage.REASON, Stage.PLAN, Stage.ACT]
        
        for stage in stage_order:
            stage_functions = stage_map.get(stage, [])
            if stage_functions:
                logger.info(f"Executing {stage.name} stage with {len(stage_functions)} functions")
                is_concurrent = concurrent_settings.get(stage, False)
                ctx = await _execute_stage_async_monitored(stage_functions, ctx, is_concurrent, stage, workflow_id)
        
        logger.info(f"Asynchronous agentic spine execution completed - {workflow_id}")
        state_manager.complete_workflow(workflow_id)
        return ctx
        
    except Exception as e:
        logger.error(f"Asynchronous agentic spine execution failed - {workflow_id}: {e}")
        state_manager.error_workflow(workflow_id, e)
        raise


async def _execute_async_prefect_tasks(tasks: List[Callable], ctx_dict: Dict[str, Any]) -> List[Any]:
    """Execute Prefect tasks asynchronously."""
    results = []
    for task in tasks:
        logger.debug(f"Executing async Prefect task: {task.name}")
        # Check if the original function (before Prefect wrapping) is async
        original_fn = getattr(task, 'fn', task)
        # Check if the task is async using Prefect's isasync attribute or function inspection
        task_isasync = getattr(task, 'isasync', False)
        fn_is_coroutine = asyncio.iscoroutinefunction(original_fn)
        is_async_task = task_isasync or fn_is_coroutine
        
        logger.debug(f"Task {task.name} async detection:")
        logger.debug(f"  - task.isasync: {task_isasync}")
        logger.debug(f"  - fn is coroutine: {fn_is_coroutine}")
        logger.debug(f"  - final is_async_task: {is_async_task}")
        
        if is_async_task:
            # For async functions, we need to call the original function directly
            logger.debug(f"Task {task.name} is async, calling original function directly")
            logger.debug(f"Original function: {original_fn}")
            logger.debug(f"Is coroutine function: {asyncio.iscoroutinefunction(original_fn)}")
            result = await original_fn(ctx_dict)
            logger.debug(f"Async task {task.name} result: {result}")
            logger.debug(f"Result type: {type(result)}")
        else:
            # For sync functions, use normal Prefect submission
            logger.debug(f"Task {task.name} is sync, using Prefect submission")
            future = task.submit(ctx_dict)
            result = future.result()
            logger.debug(f"Sync task {task.name} result: {result}")
        results.append(result)
    return results


async def _execute_concurrent_async_prefect_tasks(tasks: List[Callable], ctx_dict: Dict[str, Any]) -> List[Any]:
    """Execute Prefect tasks concurrently in async mode."""
    async def run_task(task):
        logger.debug(f"Running concurrent async Prefect task: {task.name}")
        # Check if the original function is async
        original_fn = getattr(task, 'fn', task)
        task_isasync = getattr(task, 'isasync', False)
        fn_is_coroutine = asyncio.iscoroutinefunction(original_fn)
        is_async_task = task_isasync or fn_is_coroutine
        
        logger.debug(f"Concurrent task {task.name} async detection:")
        logger.debug(f"  - task.isasync: {task_isasync}")
        logger.debug(f"  - fn is coroutine: {fn_is_coroutine}")
        logger.debug(f"  - final is_async_task: {is_async_task}")
        
        if is_async_task:
            # For async functions, call original function directly
            logger.debug(f"Concurrent task {task.name} is async, calling original function directly")
            result = await original_fn(ctx_dict)
            logger.debug(f"Concurrent async task {task.name} result: {result}")
            return result
        else:
            # For sync functions, use Prefect submission
            logger.debug(f"Concurrent task {task.name} is sync, using Prefect submission")
            future = task.submit(ctx_dict)
            result = future.result()
            logger.debug(f"Concurrent sync task {task.name} result: {result}")
            return result
    
    # Run all tasks concurrently
    return await asyncio.gather(*[run_task(task) for task in tasks])


async def _execute_async_prefect_tasks_monitored(tasks: List[Callable], ctx_dict: Dict[str, Any], stage: Stage, workflow_id: str) -> List[Any]:
    """Execute Prefect tasks asynchronously with state monitoring."""
    results = []
    state_manager = get_state_manager()
    
    for task in tasks:
        function_name = getattr(task, 'name', getattr(task, '__name__', 'unknown'))
        
        with stage_execution_context(stage, function_name, workflow_id) as execution:
            try:
                logger.debug(f"Executing async Prefect task: {task.name}")
                # Check if the original function (before Prefect wrapping) is async
                original_fn = getattr(task, 'fn', task)
                # Check if the task is async using Prefect's isasync attribute or function inspection
                task_isasync = getattr(task, 'isasync', False)
                fn_is_coroutine = asyncio.iscoroutinefunction(original_fn)
                is_async_task = task_isasync or fn_is_coroutine
                
                if is_async_task:
                    # For async functions, we need to call the original function directly
                    logger.debug(f"Task {task.name} is async, calling original function directly")
                    result = await original_fn(ctx_dict)
                    logger.debug(f"Async task {task.name} result: {result}")
                else:
                    # For sync functions, use normal Prefect submission
                    logger.debug(f"Task {task.name} is sync, using Prefect submission")
                    future = task.submit(ctx_dict)
                    result = future.result()
                    logger.debug(f"Sync task {task.name} result: {result}")
                
                execution.result = result
                results.append(result)
                
            except Exception as e:
                logger.error(f"Async Prefect task {function_name} failed: {e}")
                raise
    
    return results


async def _execute_concurrent_async_prefect_tasks_monitored(tasks: List[Callable], ctx_dict: Dict[str, Any], stage: Stage, workflow_id: str) -> List[Any]:
    """Execute Prefect tasks concurrently in async mode with state monitoring."""
    state_manager = get_state_manager()
    executions = []
    
    # Create execution trackers for all tasks
    for task in tasks:
        function_name = getattr(task, 'name', getattr(task, '__name__', 'unknown'))
        execution = state_manager.create_execution(stage, function_name, workflow_id)
        executions.append(execution)
    
    async def run_task_monitored(task, execution):
        try:
            # Mark as started and running
            state_manager.update_state(execution, StageState.STARTED)
            state_manager.update_state(execution, StageState.RUNNING)
            
            logger.debug(f"Running concurrent async Prefect task: {task.name}")
            # Check if the original function is async
            original_fn = getattr(task, 'fn', task)
            task_isasync = getattr(task, 'isasync', False)
            fn_is_coroutine = asyncio.iscoroutinefunction(original_fn)
            is_async_task = task_isasync or fn_is_coroutine
            
            if is_async_task:
                # For async functions, call original function directly
                logger.debug(f"Concurrent task {task.name} is async, calling original function directly")
                result = await original_fn(ctx_dict)
                logger.debug(f"Concurrent async task {task.name} result: {result}")
            else:
                # For sync functions, use Prefect submission
                logger.debug(f"Concurrent task {task.name} is sync, using Prefect submission")
                future = task.submit(ctx_dict)
                result = future.result()
                logger.debug(f"Concurrent sync task {task.name} result: {result}")
            
            # Mark as completed
            execution.result = result
            state_manager.update_state(execution, StageState.COMPLETED, result=result)
            return result
            
        except Exception as e:
            # Mark as error
            state_manager.update_state(execution, StageState.ERROR, error=e)
            logger.error(f"Concurrent async Prefect task {task.name} failed: {e}")
            raise
    
    # Run all tasks concurrently
    return await asyncio.gather(*[run_task_monitored(task, execution) for task, execution in zip(tasks, executions)])


@flow(name="AgenticSpineAsync")
async def agentic_spine_async_prefect(
    input_data: Any,
    functions: List[Callable],
    initial_context: Optional[Dict[str, Any]] = None,
    concurrent: Optional[Dict[Stage, bool]] = None,
    workflow_id: Optional[str] = None,
) -> Context:
    """
    Execute agentic workflow asynchronously using Prefect flow.
    
    Args:
        input_data: Input data for the workflow
        functions: List of stage functions
        initial_context: Additional initial context
        concurrent: Stage-level concurrency settings
        workflow_id: Unique identifier for workflow monitoring
        
    Returns:
        Final context after all stages
    """
    # Generate workflow ID if not provided
    if workflow_id is None:
        workflow_id = f"prefect_async_{uuid.uuid4().hex[:8]}"
    
    state_manager = get_state_manager()
    
    try:
        logger.info(f"Starting async Prefect agentic spine execution - {workflow_id}")
        state_manager.start_workflow(workflow_id)
        
        # Initialize context as dict for Prefect compatibility
        ctx_dict = {"input": input_data, **(initial_context or {})}
        
        # Collect functions by stage
        stage_map = _collect_functions(functions)
        concurrent_settings = concurrent or {}
        
        # Execute stages in order using Prefect tasks
        stage_order = [Stage.PERCEIVE, Stage.REASON, Stage.PLAN, Stage.ACT]
        
        for stage in stage_order:
            stage_functions = stage_map.get(stage, [])
            if stage_functions:
                logger.info(f"Executing {stage.name} stage with {len(stage_functions)} functions")
                
                # Convert to Prefect tasks
                tasks = [_as_task(fn) for fn in stage_functions]
                
                # Choose execution strategy
                is_concurrent = concurrent_settings.get(stage, False)
                if is_concurrent:
                    results = await _execute_concurrent_async_prefect_tasks_monitored(tasks, ctx_dict, stage, workflow_id)
                else:
                    results = await _execute_async_prefect_tasks_monitored(tasks, ctx_dict, stage, workflow_id)
                
                # Merge results into context
                logger.debug(f"Merging {len(results)} results into context for stage {stage.name}")
                for i, result in enumerate(results):
                    logger.debug(f"Merging result {i}: {result}")
                    ctx_dict = _merge_context_dict(ctx_dict, result)
                    logger.debug(f"Context after merge {i}: {list(ctx_dict.keys())}")
        
        logger.info(f"Async Prefect agentic spine execution completed - {workflow_id}")
        state_manager.complete_workflow(workflow_id)
        return Context(data=ctx_dict)
        
    except Exception as e:
        logger.error(f"Async Prefect agentic spine execution failed - {workflow_id}: {e}")
        state_manager.error_workflow(workflow_id, e)
        raise