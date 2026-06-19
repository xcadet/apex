# -*- coding: utf-8 -*-
# StarWithCoordinator operator — built on top of AFlow

import asyncio
from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class StarWithCoordinator(MASOperator):
    """
    Iterative hub-and-spoke: the coordinator actively participates across
    n_rounds rounds. Each round the coordinator broadcasts a directive to
    all workers, workers respond in parallel, coordinator reads all responses
    and produces a revised directive for the next round, final round produces
    the aggregated answer.

    Communication: coordinator -> workers (broadcast), workers -> coordinator
    (collect), no worker-to-worker communication.
    """

    def __init__(
        self,
        worker_llm: AsyncLLM,
        coordinator_llm: AsyncLLM,
        worker_prompts: List[str] = None,
        coordinator_prompt: str = "",
        n_rounds: int = 2,
        name: str = "StarWithCoordinator",
    ):
        super().__init__(name)
        self.worker_llm = worker_llm
        self.coordinator_llm = coordinator_llm
        self.num_agents = self._clamp_agents(len(worker_prompts) if worker_prompts else 0)
        self.worker_prompts = (worker_prompts or [])[: self.num_agents]
        self.coordinator_prompt = coordinator_prompt
        self.n_rounds = self._clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        directive = ""

        for round_idx in range(self.n_rounds):
            # Workers respond in parallel
            worker_tasks = [
                self._call_llm(
                    self.worker_llm,
                    prompt.format(
                        problem=problem,
                        directive=directive,
                        round=round_idx + 1,
                        agent_id=i + 1,
                    ),
                )
                for i, prompt in enumerate(self.worker_prompts)
            ]
            worker_outputs = await asyncio.gather(*worker_tasks)

            # Coordinator reads all responses
            worker_outputs_text = "\n\n".join(
                f"--- Worker {i + 1} ---\n{output}" for i, output in enumerate(worker_outputs)
            )
            coord_prompt = self.coordinator_prompt.format(
                problem=problem,
                worker_outputs=worker_outputs_text,
                round=round_idx + 1,
                is_final=(round_idx == self.n_rounds - 1),
            )
            directive = await self._call_llm(self.coordinator_llm, coord_prompt)

        return {"response": directive}
