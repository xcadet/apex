# -*- coding: utf-8 -*-
# Star operator — built on top of AFlow

import asyncio
from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class Star(MASOperator):
    """
    Parallel fan-out -> aggregation.

    Workers are fully isolated: no agent sees any other agent's output
    before the aggregation step.
    Communication: none between agents.
    """

    def __init__(
        self,
        worker_llm: AsyncLLM,
        aggregator_llm: AsyncLLM,
        num_agents: int,
        worker_prompts: List[str] = None,
        aggregator_prompt: str = "",
        name: str = "Star",
    ):
        super().__init__(name)
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = self._clamp_agents(num_agents)
        self.worker_prompts = worker_prompts or [""] * num_agents
        self.aggregator_prompt = aggregator_prompt

    async def __call__(self, problem: str) -> dict:
        # Fan-out: run all workers in parallel
        worker_tasks = [
            self._call_llm(
                self.worker_llm,
                prompt.format(problem=problem),
            )
            for prompt in self.worker_prompts[: self.num_agents]
        ]
        worker_outputs = await asyncio.gather(*worker_tasks)

        # Aggregation
        solutions_text = "\n\n".join(f"--- Agent {i + 1} ---\n{output}" for i, output in enumerate(worker_outputs))
        agg_prompt = self.aggregator_prompt.format(
            problem=problem,
            worker_outputs=solutions_text,
        )
        result = await self._call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}
