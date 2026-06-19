import asyncio
from typing import List

from scripts.formatter import TextFormatter
from scripts.async_llm import AsyncLLM


# ── Safety limits for MAS operators ──────────────────────────────────────────
MAX_ROUNDS = 5
MAX_AGENTS = 10


def _clamp_rounds(n: int) -> int:
    return max(1, min(n, MAX_ROUNDS))


def _clamp_agents(n: int) -> int:
    return max(1, min(n, MAX_AGENTS))


# ── MAS topology operators ───────────────────────────────────────────────────
# These operators use a worker LLM and an aggregator LLM.
# The LLMs are passed directly — the workflow exposes self.llm (worker)
# and self.aggregator_llm for use when constructing these operators.


async def _call_llm(llm: AsyncLLM, prompt: str) -> str:
    """Call an AsyncLLM with TextFormatter and return the response text."""
    formatter = TextFormatter()
    response = await llm.call_with_format(prompt, formatter)
    if isinstance(response, dict):
        return response.get("response", "")
    return str(response)


class Sequential:
    """Linear pipeline: each step receives the previous step's output."""

    def __init__(self, llm: AsyncLLM, num_rounds: int = 1, prompts: List[str] = None):
        self.llm = llm
        self.num_rounds = _clamp_rounds(num_rounds)
        self.prompts = prompts or []

    async def __call__(self, problem: str) -> dict:
        current_output = problem
        for _ in range(self.num_rounds):
            for prompt in self.prompts:
                full_prompt = prompt.format(problem=problem, previous_output=current_output)
                current_output = await _call_llm(self.llm, full_prompt)
        return {"response": current_output}


class Star:
    """Parallel fan-out to isolated workers, then aggregation."""

    def __init__(self, worker_llm: AsyncLLM, aggregator_llm: AsyncLLM,
                 num_agents: int = 3, worker_prompts: List[str] = None,
                 aggregator_prompt: str = ""):
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = _clamp_agents(num_agents)
        self.worker_prompts = worker_prompts or [""] * self.num_agents
        self.aggregator_prompt = aggregator_prompt

    async def __call__(self, problem: str) -> dict:
        tasks = [
            _call_llm(self.worker_llm, p.format(problem=problem))
            for p in self.worker_prompts[:self.num_agents]
        ]
        worker_outputs = await asyncio.gather(*tasks)
        solutions_text = "\n\n".join(
            f"--- Agent {i+1} ---\n{out}" for i, out in enumerate(worker_outputs)
        )
        agg_prompt = self.aggregator_prompt.format(problem=problem, worker_outputs=solutions_text)
        result = await _call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}


class SharedMemory:
    """Agents write sequentially to a shared document, then aggregation."""

    def __init__(self, worker_llm: AsyncLLM, aggregator_llm: AsyncLLM,
                 num_agents: int = 3, num_rounds: int = 1,
                 worker_prompts: List[str] = None, aggregator_prompt: str = ""):
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = _clamp_agents(num_agents)
        self.num_rounds = _clamp_rounds(num_rounds)
        self.worker_prompts = worker_prompts or [""] * self.num_agents
        self.aggregator_prompt = aggregator_prompt

    async def __call__(self, problem: str) -> dict:
        document = ""
        for round_idx in range(self.num_rounds):
            for agent_idx in range(self.num_agents):
                prompt = self.worker_prompts[agent_idx].format(
                    problem=problem, document=document,
                    agent_id=agent_idx + 1, round=round_idx + 1,
                )
                contribution = await _call_llm(self.worker_llm, prompt)
                document += f"\n\n[Agent {agent_idx+1}, Round {round_idx+1}]\n{contribution}"
        agg_prompt = self.aggregator_prompt.format(problem=problem, document=document)
        result = await _call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}


class Debate:
    """All-to-all debate over n_rounds, then aggregation."""

    def __init__(self, worker_llm: AsyncLLM, aggregator_llm: AsyncLLM,
                 num_agents: int = 3, worker_prompts: List[str] = None,
                 aggregator_prompt: str = "", n_rounds: int = 2):
        self.worker_llm = worker_llm
        self.aggregator_llm = aggregator_llm
        self.num_agents = _clamp_agents(num_agents)
        self.worker_prompts = worker_prompts or [""] * self.num_agents
        self.aggregator_prompt = aggregator_prompt
        self.n_rounds = _clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        proposals = [""] * self.num_agents
        for round_idx in range(self.n_rounds):
            new_proposals = []
            for agent_idx in range(self.num_agents):
                all_text = "\n\n".join(
                    f"--- Agent {i+1} ---\n{p}" for i, p in enumerate(proposals) if p
                )
                full_prompt = self.worker_prompts[agent_idx].format(
                    problem=problem, all_proposals=all_text,
                    round=round_idx + 1, agent_id=agent_idx + 1,
                )
                out = await _call_llm(self.worker_llm, full_prompt)
                new_proposals.append(out)
            proposals = new_proposals
        all_text = "\n\n".join(
            f"--- Agent {i+1} ---\n{p}" for i, p in enumerate(proposals)
        )
        agg_prompt = self.aggregator_prompt.format(problem=problem, all_proposals=all_text)
        result = await _call_llm(self.aggregator_llm, agg_prompt)
        return {"response": result}


class StarWithCoordinator:
    """Iterative hub-and-spoke with active coordinator."""

    def __init__(self, worker_llm: AsyncLLM, coordinator_llm: AsyncLLM,
                 worker_prompts: List[str] = None, coordinator_prompt: str = "",
                 n_rounds: int = 2):
        self.worker_llm = worker_llm
        self.coordinator_llm = coordinator_llm
        self.num_agents = _clamp_agents(len(worker_prompts) if worker_prompts else 0)
        self.worker_prompts = (worker_prompts or [])[:self.num_agents]
        self.coordinator_prompt = coordinator_prompt
        self.n_rounds = _clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        directive = ""
        for round_idx in range(self.n_rounds):
            tasks = [
                _call_llm(self.worker_llm, p.format(
                    problem=problem, directive=directive,
                    round=round_idx + 1, agent_id=i + 1,
                ))
                for i, p in enumerate(self.worker_prompts)
            ]
            worker_outputs = await asyncio.gather(*tasks)
            outputs_text = "\n\n".join(
                f"--- Worker {i+1} ---\n{out}" for i, out in enumerate(worker_outputs)
            )
            coord_prompt = self.coordinator_prompt.format(
                problem=problem, worker_outputs=outputs_text,
                round=round_idx + 1, is_final=(round_idx == self.n_rounds - 1),
            )
            directive = await _call_llm(self.coordinator_llm, coord_prompt)
        return {"response": directive}


class DebateWithModerator:
    """Moderated all-to-all debate."""

    def __init__(self, worker_llm: AsyncLLM, moderator_llm: AsyncLLM,
                 agent_prompts: List[str] = None, moderator_prompt: str = "",
                 n_rounds: int = 2):
        self.worker_llm = worker_llm
        self.moderator_llm = moderator_llm
        self.num_agents = _clamp_agents(len(agent_prompts) if agent_prompts else 0)
        self.agent_prompts = (agent_prompts or [])[:self.num_agents]
        self.moderator_prompt = moderator_prompt
        self.n_rounds = _clamp_rounds(n_rounds)

    async def __call__(self, problem: str) -> dict:
        proposals = [""] * self.num_agents
        moderator_input = ""
        for round_idx in range(self.n_rounds):
            new_proposals = []
            for agent_idx in range(self.num_agents):
                all_text = "\n\n".join(
                    f"--- Agent {i+1} ---\n{p}" for i, p in enumerate(proposals) if p
                )
                full_prompt = self.agent_prompts[agent_idx].format(
                    problem=problem, all_proposals=all_text,
                    moderator_input=moderator_input,
                    round=round_idx + 1, agent_id=agent_idx + 1,
                )
                out = await _call_llm(self.worker_llm, full_prompt)
                new_proposals.append(out)
            proposals = new_proposals
            all_text = "\n\n".join(
                f"--- Agent {i+1} ---\n{p}" for i, p in enumerate(proposals)
            )
            mod_prompt = self.moderator_prompt.format(
                problem=problem, all_proposals=all_text,
                round=round_idx + 1, is_final=(round_idx == self.n_rounds - 1),
            )
            moderator_input = await _call_llm(self.moderator_llm, mod_prompt)
        return {"response": moderator_input}
