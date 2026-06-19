from typing import Literal
import workspace._enigmata_base.workflows.template.operator as operator
import workspace._enigmata_base.workflows.round_1.prompt as prompt_custom
from scripts.async_llm import create_llm_instance

from scripts.evaluator import DatasetType

class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
        aggregator_llm_config=None,
    ) -> None:
        self.name = name
        self.dataset = dataset
        self.llm = create_llm_instance(llm_config)
        self.aggregator_llm = create_llm_instance(aggregator_llm_config) if aggregator_llm_config else self.llm

    async def __call__(self, problem: str):
        """
        Seed workflow: single-step Sequential as baseline.
        """
        seq = operator.Sequential(
            llm=self.llm,
            num_rounds=1,
            prompts=["{problem}"],
        )
        solution = await seq(problem)
        worker_usage = self.llm.get_usage_delta()
        if self.aggregator_llm is self.llm:
            aggregator_usage = {"total_input_tokens": 0, "total_output_tokens": 0, "total_cost": 0.0}
        else:
            aggregator_usage = self.aggregator_llm.get_usage_delta()
        return solution['response'], {
            "worker": worker_usage,
            "aggregator": aggregator_usage,
        }
