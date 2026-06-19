# -*- coding: utf-8 -*-
# SharedMemory operator — built on top of AFlow

from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class SharedMemory(MASOperator):
    """
    Agents write sequentially to a shared document, each reading the current
    state before contributing. The aggregator reads the final document.

    Communication: indirect — agents communicate through the document state.
    """

    def __init__(
        self,
        worker_llm: AsyncLLM,
        aggregator_llm: AsyncLLM,
        num_agents: int,
        num_rounds: int = 1,
        worker_prompts: List[str] = None,
        aggregator_prompt: str = "",
        name: str = "SharedMemory",
    ):
        super().__init__(name)
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = self._clamp_agents(num_agents)
        self.num_rounds = self._clamp_rounds(num_rounds)
        self.worker_prompts = worker_prompts or [""] * num_agents
        self.aggregator_prompt = aggregator_prompt

    async def __call__(self, problem: str) -> dict:
        document = ""

        for round_idx in range(self.num_rounds):
            for agent_idx in range(self.num_agents):
                prompt = self.worker_prompts[agent_idx]
                full_prompt = prompt.format(
                    problem=problem,
                    document=document,
                    agent_id=agent_idx + 1,
                    round=round_idx + 1,
                )
                contribution = await self._call_llm(self.worker_llm, full_prompt)
                document += f"\n\n[Agent {agent_idx + 1}, Round {round_idx + 1}]\n{contribution}"

        # Aggregation on final document
        agg_prompt = self.aggregator_prompt.format(
            problem=problem,
            document=document,
        )
        result = await self._call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}
