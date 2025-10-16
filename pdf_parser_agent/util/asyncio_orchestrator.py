import asyncio
from typing import Dict, Callable, List
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

class AsyncioOrchestrator:
    def __init__(self, flow: Dict, registry: Dict[str, Dict[str, Callable]]):
        self.flow = flow
        self.registry = registry

    async def _run_group(self, stage: str, group: dict, vo: PdfParserVO):
        mode = group.get("mode", "sequential")
        names: List[str] = group.get("tasks", [])
        funcs = [self.registry.get(stage, {}).get(n) for n in names]
        funcs = [f for f in funcs if f]

        if mode == "parallel":
            await asyncio.gather(*[f(vo) for f in funcs])
            return vo
        for f in funcs:
            vo = await f(vo)
        return vo

    async def run(self, vo: PdfParserVO) -> PdfParserVO:
        for stage, groups in self.flow.items():
            for g in groups:
                vo = await self._run_group(stage, g, vo)
        return vo