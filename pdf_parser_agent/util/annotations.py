from functools import wraps
from typing import Callable, Dict, Optional

TOUCHPOINTS: Dict[str, Dict[str, Callable]] = {}
 
def touchpoint(
    stage: str,
    task: str,
    use_llm: bool = False,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    def dec(fn: Callable):
        # Attach metadata for orchestration
        fn._touchpoint_meta = {
            "stage": layer,
            "task": task,
            "use_llm": use_llm,
            "model": model,
            "system_prompt": system_prompt,
        }
 
        # Register in global touchpoints registry
        TOUCHPOINTS.setdefault(stage, {})[task] = fn
 
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
 
        return wrapper
 
    return dec
 
 
def agent(name: str, description: str = None):
    def dec(cls_or_fn: Callable):
        cls_or_fn._agent_name = name
        if description:
            cls_or_fn._agent_description = description
        return cls_or_fn
    return dec