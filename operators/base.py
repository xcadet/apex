# -*- coding: utf-8 -*-
# Base class for multi-agent operators — built on top of AFlow

from scripts.async_llm import AsyncLLM
from scripts.operators import Operator
from scripts.formatter import TextFormatter

# Safety limits for MAS operators
MAX_ROUNDS = 5
MAX_AGENTS = 10


class MASOperator(Operator):
    """
    Base class for multi-agent topology operators.

    Extends AFlow's Operator but allows targeting different pre-configured
    AsyncLLM instances per call (e.g. worker vs. aggregator/coordinator).
    """

    def __init__(self, name: str = "MASOperator"):
        # We don't pass a single llm to super(); each subclass manages its own.
        self.name = name

    @staticmethod
    def _clamp_rounds(n_rounds: int) -> int:
        return max(1, min(n_rounds, MAX_ROUNDS))

    @staticmethod
    def _clamp_agents(num_agents: int) -> int:
        return max(1, min(num_agents, MAX_AGENTS))

    async def _call_llm(self, llm: AsyncLLM, prompt: str) -> str:
        """Call a specific AsyncLLM instance and return the response text."""
        formatter = TextFormatter()
        response = await llm.call_with_format(prompt, formatter)
        if isinstance(response, dict):
            return response.get("response", "")
        return str(response)
