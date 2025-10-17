import asyncio
from typing import Dict, Callable, List, Any

class AsyncioOrchestrator:
    def __init__(self, flow: Dict, registry: Dict[str, Dict[str, Callable]]):
        self.flow = flow
        self.registry = registry

    async def _run_group(self, stage: str, group: dict, context: Dict[str, Any]):
        mode = group.get("mode", "sequential")
        names: List[str] = group.get("tasks", [])
        funcs = [self.registry.get(stage, {}).get(n) for n in names]
        funcs = [f for f in funcs if f]

        if mode == "parallel":
            await asyncio.gather(*[f(context) for f in funcs])
            return context
        for f in funcs:
            context = await f(context)
        return context

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        for stage, groups in self.flow.items():
            for g in groups:
                context = await self._run_group(stage, g, context)
        return context