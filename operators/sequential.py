# -*- coding: utf-8 -*-
# Sequential operator — built on top of AFlow

from typing import List

from scripts.async_llm import AsyncLLM
from operators.base import MASOperator


class Sequential(MASOperator):
    """
    Agent(Prompt 1) -> Agent(Prompt 2) -> ... -> Agent(Prompt N)

    Each step receives the previous step's output as context.
    The number of steps is len(prompts), repeated for num_rounds.
    """

    def __init__(
        self,
        llm: AsyncLLM,
        num_rounds: int = 1,
        prompts: List[str] = None,
        name: str = "Sequential",
    ):
        super().__init__(name)
        self.llm = llm
        self.num_rounds = self._clamp_rounds(num_rounds)
        self.prompts = prompts or []

    async def __call__(self, problem: str) -> dict:
        current_output = problem

        for _ in range(self.num_rounds):
            for prompt in self.prompts:
                full_prompt = prompt.format(
                    problem=problem,
                    previous_output=current_output,
                )
                current_output = await self._call_llm(self.llm, full_prompt)

        return {"response": current_output}
