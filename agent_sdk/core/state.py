"""
Stage state management and monitoring system.

This module provides comprehensive state tracking for agentic workflow stages,
allowing real-time monitoring of stage execution states.
"""

from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import threading
from contextlib import contextmanager

from .stages import Stage
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StageState(Enum):
    """Enumeration of possible stage states."""
    PENDING = "pending"
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class StageExecution:
    """Information about a single stage execution."""
    stage: Stage
    state: StageState
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    result: Optional[Any] = None
    function_name: Optional[str] = None
    execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_finished(self) -> bool:
        """Check if the stage execution is finished."""
        return self.state in {StageState.COMPLETED, StageState.ERROR, StageState.CANCELLED, StageState.SKIPPED}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage": self.stage.name,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error": str(self.error) if self.error else None,
            "function_name": self.function_name,
            "execution_id": self.execution_id,
            "metadata": self.metadata,
            "is_finished": self.is_finished
        }


class StageStateObserver:
    """Observer interface for stage state changes."""
    
    def on_stage_state_changed(self, execution: StageExecution) -> None:
        """Called when a stage state changes."""
        pass
    
    def on_workflow_started(self, workflow_id: str) -> None:
        """Called when a workflow starts."""
        pass
    
    def on_workflow_completed(self, workflow_id: str, executions: List[StageExecution]) -> None:
        """Called when a workflow completes."""
        pass
    
    def on_workflow_error(self, workflow_id: str, error: Exception) -> None:
        """Called when a workflow encounters an error."""
        pass


class LoggingObserver(StageStateObserver):
    """Observer that logs stage state changes."""
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = get_logger(f"{__name__}.LoggingObserver")
        
    def on_stage_state_changed(self, execution: StageExecution) -> None:
        """Log stage state changes."""
        if execution.state == StageState.STARTED:
            self.logger.info(f"🚀 Stage {execution.stage.name} started - {execution.function_name}")
        elif execution.state == StageState.RUNNING:
            self.logger.info(f"⚡ Stage {execution.stage.name} running - {execution.function_name}")
        elif execution.state == StageState.COMPLETED:
            duration = execution.duration or 0
            self.logger.info(f"✅ Stage {execution.stage.name} completed in {duration:.3f}s - {execution.function_name}")
        elif execution.state == StageState.ERROR:
            self.logger.error(f"❌ Stage {execution.stage.name} failed - {execution.function_name}: {execution.error}")
        elif execution.state == StageState.CANCELLED:
            self.logger.warning(f"⏹️ Stage {execution.stage.name} cancelled - {execution.function_name}")
        elif execution.state == StageState.SKIPPED:
            self.logger.info(f"⏭️ Stage {execution.stage.name} skipped - {execution.function_name}")
    
    def on_workflow_started(self, workflow_id: str) -> None:
        """Log workflow start."""
        self.logger.info(f"🎬 Workflow {workflow_id} started")
    
    def on_workflow_completed(self, workflow_id: str, executions: List[StageExecution]) -> None:
        """Log workflow completion."""
        total_duration = sum(e.duration or 0 for e in executions if e.duration)
        completed_count = sum(1 for e in executions if e.state == StageState.COMPLETED)
        error_count = sum(1 for e in executions if e.state == StageState.ERROR)
        
        self.logger.info(f"🏁 Workflow {workflow_id} completed: {completed_count} succeeded, {error_count} failed, {total_duration:.3f}s total")
    
    def on_workflow_error(self, workflow_id: str, error: Exception) -> None:
        """Log workflow error."""
        self.logger.error(f"💥 Workflow {workflow_id} failed: {error}")


class MetricsObserver(StageStateObserver):
    """Observer that collects metrics and statistics."""
    
    def __init__(self):
        self.metrics = {
            "total_executions": 0,
            "completed_executions": 0,
            "failed_executions": 0,
            "total_duration": 0.0,
            "stage_counts": {},
            "error_counts": {},
            "average_durations": {}
        }
        self._lock = threading.Lock()
    
    def on_stage_state_changed(self, execution: StageExecution) -> None:
        """Collect metrics from stage state changes."""
        with self._lock:
            if execution.state == StageState.STARTED:
                self.metrics["total_executions"] += 1
                stage_name = execution.stage.name
                self.metrics["stage_counts"][stage_name] = self.metrics["stage_counts"].get(stage_name, 0) + 1
            
            elif execution.state == StageState.COMPLETED:
                self.metrics["completed_executions"] += 1
                if execution.duration:
                    self.metrics["total_duration"] += execution.duration
                    stage_name = execution.stage.name
                    if stage_name not in self.metrics["average_durations"]:
                        self.metrics["average_durations"][stage_name] = []
                    self.metrics["average_durations"][stage_name].append(execution.duration)
            
            elif execution.state == StageState.ERROR:
                self.metrics["failed_executions"] += 1
                error_type = type(execution.error).__name__ if execution.error else "Unknown"
                self.metrics["error_counts"][error_type] = self.metrics["error_counts"].get(error_type, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._lock:
            # Calculate average durations
            avg_durations = {}
            for stage, durations in self.metrics["average_durations"].items():
                if durations:
                    avg_durations[stage] = sum(durations) / len(durations)
            
            return {
                **self.metrics,
                "success_rate": (
                    self.metrics["completed_executions"] / max(self.metrics["total_executions"], 1)
                ) * 100,
                "average_durations": avg_durations
            }


class StageStateManager:
    """Manages stage state tracking and observer notifications."""
    
    def __init__(self):
        self.observers: List[StageStateObserver] = []
        self.executions: Dict[str, List[StageExecution]] = {}
        self._lock = threading.Lock()
        self._execution_counter = 0
    
    def add_observer(self, observer: StageStateObserver) -> None:
        """Add a state observer."""
        self.observers.append(observer)
    
    def remove_observer(self, observer: StageStateObserver) -> None:
        """Remove a state observer."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def create_execution(self, stage: Stage, function_name: str, workflow_id: str = "default") -> StageExecution:
        """Create a new stage execution tracker."""
        with self._lock:
            self._execution_counter += 1
            execution_id = f"{workflow_id}_{stage.name}_{self._execution_counter}"
        
        execution = StageExecution(
            stage=stage,
            state=StageState.PENDING,
            function_name=function_name,
            execution_id=execution_id
        )
        
        with self._lock:
            if workflow_id not in self.executions:
                self.executions[workflow_id] = []
            self.executions[workflow_id].append(execution)
        
        return execution
    
    def update_state(self, execution: StageExecution, new_state: StageState, 
                    error: Optional[Exception] = None, result: Optional[Any] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update the state of a stage execution."""
        old_state = execution.state
        execution.state = new_state
        
        if new_state == StageState.STARTED:
            execution.start_time = datetime.now()
        elif new_state in {StageState.COMPLETED, StageState.ERROR, StageState.CANCELLED}:
            execution.end_time = datetime.now()
        
        if error:
            execution.error = error
        if result is not None:
            execution.result = result
        if metadata:
            execution.metadata.update(metadata)
        
        # Notify observers
        for observer in self.observers:
            try:
                observer.on_stage_state_changed(execution)
            except Exception as e:
                logger.error(f"Observer {observer} failed to handle state change: {e}")
    
    def start_workflow(self, workflow_id: str) -> None:
        """Mark the start of a workflow."""
        for observer in self.observers:
            try:
                observer.on_workflow_started(workflow_id)
            except Exception as e:
                logger.error(f"Observer {observer} failed to handle workflow start: {e}")
    
    def complete_workflow(self, workflow_id: str) -> None:
        """Mark the completion of a workflow."""
        executions = self.executions.get(workflow_id, [])
        for observer in self.observers:
            try:
                observer.on_workflow_completed(workflow_id, executions)
            except Exception as e:
                logger.error(f"Observer {observer} failed to handle workflow completion: {e}")
    
    def error_workflow(self, workflow_id: str, error: Exception) -> None:
        """Mark a workflow error."""
        for observer in self.observers:
            try:
                observer.on_workflow_error(workflow_id, error)
            except Exception as e:
                logger.error(f"Observer {observer} failed to handle workflow error: {e}")
    
    def get_executions(self, workflow_id: str) -> List[StageExecution]:
        """Get all executions for a workflow."""
        return self.executions.get(workflow_id, [])
    
    def get_execution_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get a summary of workflow execution."""
        executions = self.get_executions(workflow_id)
        
        if not executions:
            return {"workflow_id": workflow_id, "status": "not_found"}
        
        total_duration = sum(e.duration or 0 for e in executions if e.duration)
        completed = [e for e in executions if e.state == StageState.COMPLETED]
        errors = [e for e in executions if e.state == StageState.ERROR]
        running = [e for e in executions if e.state in {StageState.STARTED, StageState.RUNNING}]
        
        return {
            "workflow_id": workflow_id,
            "total_stages": len(executions),
            "completed": len(completed),
            "errors": len(errors),
            "running": len(running),
            "total_duration": total_duration,
            "status": "running" if running else "completed" if not errors else "failed",
            "executions": [e.to_dict() for e in executions]
        }


# Global state manager instance
_global_state_manager = StageStateManager()

# Add default logging observer
_global_state_manager.add_observer(LoggingObserver())


def get_state_manager() -> StageStateManager:
    """Get the global stage state manager."""
    return _global_state_manager


@contextmanager
def stage_execution_context(stage: Stage, function_name: str, workflow_id: str = "default"):
    """Context manager for tracking stage execution."""
    state_manager = get_state_manager()
    execution = state_manager.create_execution(stage, function_name, workflow_id)
    
    try:
        # Mark as started
        state_manager.update_state(execution, StageState.STARTED)
        state_manager.update_state(execution, StageState.RUNNING)
        
        yield execution
        
        # Mark as completed if no exception
        state_manager.update_state(execution, StageState.COMPLETED)
        
    except Exception as e:
        # Mark as error
        state_manager.update_state(execution, StageState.ERROR, error=e)
        raise


def configure_monitoring(enable_logging: bool = True, enable_metrics: bool = True,
                        custom_observers: Optional[List[StageStateObserver]] = None) -> StageStateManager:
    """Configure stage monitoring with observers."""
    state_manager = get_state_manager()
    
    # Clear existing observers
    state_manager.observers.clear()
    
    # Add default observers
    if enable_logging:
        state_manager.add_observer(LoggingObserver())
    
    if enable_metrics:
        state_manager.add_observer(MetricsObserver())
    
    # Add custom observers
    if custom_observers:
        for observer in custom_observers:
            state_manager.add_observer(observer)
    
    return state_manager


def get_workflow_status(workflow_id: str = "default") -> Dict[str, Any]:
    """Get the current status of a workflow."""
    return get_state_manager().get_execution_summary(workflow_id)


def get_metrics() -> Dict[str, Any]:
    """Get current execution metrics."""
    state_manager = get_state_manager()
    for observer in state_manager.observers:
        if isinstance(observer, MetricsObserver):
            return observer.get_metrics()
    return {"error": "MetricsObserver not found"}