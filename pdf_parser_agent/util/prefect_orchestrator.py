from __future__ import annotations
from typing import Dict, Callable, List, Any
import asyncio
from prefect import task, flow
from context_agent.vo.context_vo import ContextVO

class PrefectOrchestrator:
    def __init__(self, flow_def: Dict[str, List[Dict[str, Any]]], registry: Dict[str, Dict[str, Callable]]):
        self.flow_def = flow_def
        self.registry = registry

    def _build_task(self, stage: str, name: str, fn: Callable):
        @task(
            name=f"{stage}.{name}",
            retries=1,
            retry_delay_seconds=3,
            persist_result=False,
        )
        async def _wrapped(vo: ContextVO) -> ContextVO:
            return await fn(vo)
        return _wrapped

    async def _run_group(self, stage: str, group: Dict[str, Any], vo: ContextVO) -> ContextVO:
        mode = group.get("mode", "sequential")
        task_names = group.get("tasks", [])
        funcs = [self.registry.get(stage, {}).get(t) for t in task_names if self.registry.get(stage, {}).get(t)]
        if not funcs:
            return vo
        if mode == "parallel":
            tasks = [self._build_task(stage, t.__name__, t)(submit)(vo) for t in funcs]
            results = await asyncio.gather(*[task.result() for task in tasks])
            merged_vo = results[0]
            for r in results[1:]:
                merged_vo.stage_data.update(r.stage_data)
                merged_vo.meta.update(r.meta)
                merged_vo.sources.extend(r.sources)
            return merged_vo
        for fn in funcs:
            _t = self._build_task(stage, fn.__name__, fn)
            vo = await _t(vo)
        return vo

    @flow(name="context_agent_flow")
    async def _prefect_flow(self, vo: ContextVO) -> ContextVO:
        for stage, groups in self.flow_def.items():
            for group in groups:
                vo = await self._run_group(stage, group, vo)
        return vo
    async def run(self, vo: ContextVO) -> ContextVO:
        return await self._prefect_flow(vo)