# -*- coding: utf-8 -*-
# Debate operator — built on top of AFlow

from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class Debate(MASOperator):
    """
    All-to-all explicit communication over n_rounds rounds. Each agent
    receives all other agents' current proposals before producing a revised
    response. A final aggregator call produces the answer.

    Communication: direct agent-to-agent, full proposal visibility.
    """

    def __init__(
        self,
        worker_llm: AsyncLLM,
        aggregator_llm: AsyncLLM,
        num_agents: int,
        worker_prompts: List[str] = None,
        aggregator_prompt: str = "",
        n_rounds: int = 2,
        name: str = "Debate",
    ):
        super().__init__(name)
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = self._clamp_agents(num_agents)
        self.worker_prompts = worker_prompts or [""] * self.num_agents
        self.aggregator_prompt = aggregator_prompt
        self.n_rounds = self._clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        proposals = [""] * self.num_agents

        for round_idx in range(self.n_rounds):
            new_proposals = []
            for agent_idx in range(self.num_agents):
                all_proposals_text = "\n\n".join(f"--- Agent {i + 1} ---\n{p}" for i, p in enumerate(proposals) if p)
                full_prompt = self.worker_prompts[agent_idx].format(
                    problem=problem,
                    all_proposals=all_proposals_text,
                    round=round_idx + 1,
                    agent_id=agent_idx + 1,
                )
                output = await self._call_llm(self.worker_llm, full_prompt)
                new_proposals.append(output)

            proposals = new_proposals

        # Final aggregation
        all_proposals_text = "\n\n".join(f"--- Agent {i + 1} ---\n{p}" for i, p in enumerate(proposals))
        agg_prompt = self.aggregator_prompt.format(
            problem=problem,
            all_proposals=all_proposals_text,
        )
        result = await self._call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}
