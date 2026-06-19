# -*- coding: utf-8 -*-
# DebateWithModerator operator — built on top of AFlow

from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class DebateWithModerator(MASOperator):
    """
    Moderated all-to-all debate: the moderator actively participates in every
    round by injecting a summary, challenge, or steering prompt after agents
    exchange proposals. Each agent receives both peer proposals and the
    moderator's intervention before producing its next response.

    Communication: direct agent-to-agent + moderator-to-all each round.
    """

    def __init__(
        self,
        worker_llm: AsyncLLM,
        moderator_llm: AsyncLLM,
        agent_prompts: List[str] = None,
        moderator_prompt: str = "",
        n_rounds: int = 2,
        name: str = "DebateWithModerator",
    ):
        super().__init__(name)
        self.worker_llm = worker_llm
        self.moderator_llm = moderator_llm
        self.num_agents = self._clamp_agents(len(agent_prompts) if agent_prompts else 0)
        self.agent_prompts = (agent_prompts or [])[: self.num_agents]
        self.moderator_prompt = moderator_prompt
        self.n_rounds = self._clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        proposals = [""] * self.num_agents
        moderator_input = ""

        for round_idx in range(self.n_rounds):
            # Each agent produces a revised proposal
            new_proposals = []
            for agent_idx in range(self.num_agents):
                all_proposals_text = "\n\n".join(f"--- Agent {i + 1} ---\n{p}" for i, p in enumerate(proposals) if p)
                full_prompt = self.agent_prompts[agent_idx].format(
                    problem=problem,
                    all_proposals=all_proposals_text,
                    moderator_input=moderator_input,
                    round=round_idx + 1,
                    agent_id=agent_idx + 1,
                )
                output = await self._call_llm(self.worker_llm, full_prompt)
                new_proposals.append(output)

            proposals = new_proposals

            # Moderator intervention
            all_proposals_text = "\n\n".join(f"--- Agent {i + 1} ---\n{p}" for i, p in enumerate(proposals))
            mod_prompt = self.moderator_prompt.format(
                problem=problem,
                all_proposals=all_proposals_text,
                round=round_idx + 1,
                is_final=(round_idx == self.n_rounds - 1),
            )
            moderator_input = await self._call_llm(self.moderator_llm, mod_prompt)

        # The final moderator output is the aggregated answer
        return {"response": moderator_input}
