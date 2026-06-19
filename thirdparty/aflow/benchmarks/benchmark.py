import asyncio
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Tuple

import aiofiles
import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from scripts.logs import logger
from scripts.utils.common import write_json_file


class BaseBenchmark(ABC):
    def __init__(self, name: str, file_path: str, log_path: str):
        self.name = name
        self.file_path = file_path
        self.log_path = log_path

    PASS = "PASS"
    FAIL = "FAIL"

    async def load_data(self, specific_indices: List[int] = None) -> List[dict]:
        data = []
        async with aiofiles.open(self.file_path, mode="r", encoding="utf-8") as file:
            async for line in file:
                data.append(json.loads(line))
        if specific_indices is not None:
            filtered_data = [data[i] for i in specific_indices if i < len(data)]
            return filtered_data
        return data

    def save_results_to_csv(self, results: List[Tuple[Any, ...]], columns: List[str]):
        df = pd.DataFrame(results, columns=columns)
        avg_score = df["score"].mean()

        # Aggregate usage per role: usage may be per-role dict, flat dict, or float (legacy)
        roles = ("worker", "aggregator")
        total_usage = {
            role: {"total_input_tokens": 0, "total_output_tokens": 0, "total_cost": 0.0}
            for role in roles
        }
        for usage in df["cost"]:
            if isinstance(usage, dict) and any(r in usage for r in roles):
                # Per-role usage: {"worker": {...}, "aggregator": {...}}
                for role in roles:
                    role_usage = usage.get(role, {})
                    for k in total_usage[role]:
                        total_usage[role][k] += role_usage.get(k, 0)
            elif isinstance(usage, dict):
                # Flat usage dict (legacy) — attribute to worker
                for k in total_usage["worker"]:
                    total_usage["worker"][k] += usage.get(k, 0)
            else:
                total_usage["worker"]["total_cost"] += float(usage)

        t_cost = sum(total_usage[r]["total_cost"] for r in roles)
        a_cost = t_cost / len(df) if len(df) > 0 else 0

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{avg_score:.5f}_{current_time}.csv"
        output_file = os.path.join(self.log_path, filename)
        df.to_csv(output_file, index=False)
        logger.info(f"Results saved to {output_file}")
        return avg_score, a_cost, t_cost, total_usage

    def log_mismatch(
        self,
        problem: str,
        expected_output: Any,
        prediction: str,
        extracted_output: Any,
        extract_answer_code: str = "None",
    ):
        log_data = {
            "question": problem,
            "right_answer": expected_output,
            "model_output": prediction,
            "extracted_output": extracted_output,
            "extract_answer_code": extract_answer_code,
        }
        log_file = Path(self.log_path) / "log.json"
        if log_file.exists():
            with log_file.open("r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        data.append(log_data)
        write_json_file(log_file, data, encoding="utf-8", indent=4)

    @abstractmethod
    async def evaluate_problem(self, problem: dict, agent: Callable) -> Tuple[Any, ...]:
        pass

    @abstractmethod
    def calculate_score(self, expected_output: Any, prediction: Any) -> Tuple[float, Any]:
        pass

    @abstractmethod
    def get_result_columns(self) -> List[str]:
        pass

    async def evaluate_all_problems(self, data: List[dict], agent: Callable, max_concurrent_tasks: int = 50):
        semaphore = asyncio.Semaphore(max_concurrent_tasks)
        # Best-effort import — the puzzle_idx contextvar lets call_tracking
        # tag every LLM call with the puzzle that triggered it, so the
        # parallel evaluations can be reconstructed post-hoc. The CallBudget
        # is per-puzzle (one fresh instance per task) so siblings don't share
        # counters and a runaway workflow only kills its own puzzle.
        try:
            from call_tracking import (  # type: ignore
                set_puzzle_idx,
                set_call_budget,
                get_workflow_call_limit,
                CallBudget,
            )
            workflow_call_limit = get_workflow_call_limit()
        except ImportError:
            from contextlib import nullcontext

            def set_puzzle_idx(_):
                return nullcontext()

            def set_call_budget(_):
                return nullcontext()

            CallBudget = None  # type: ignore
            workflow_call_limit = None

        # ctx_usage_scope is the contextvar AsyncLLM.get_usage_delta() reads.
        # Each puzzle task starts with a fresh empty dict so concurrent
        # puzzles don't see each other's token counts.
        from scripts.async_llm import ctx_usage_scope

        async def sem_evaluate(idx, problem):
            async with semaphore:
                budget = CallBudget(workflow_call_limit) if CallBudget is not None else None
                scope_token = ctx_usage_scope.set({})
                try:
                    with set_puzzle_idx(idx), set_call_budget(budget):
                        return await self.evaluate_problem(problem, agent)
                finally:
                    ctx_usage_scope.reset(scope_token)

        tasks = [sem_evaluate(i, problem) for i, problem in enumerate(data)]
        return await tqdm_asyncio.gather(*tasks, desc=f"Evaluating {self.name} problems", total=len(data))

    async def run_evaluation(self, agent: Callable, va_list: List[int], max_concurrent_tasks: int = 50):
        data = await self.load_data(va_list)
        results = await self.evaluate_all_problems(data, agent, max_concurrent_tasks)
        columns = self.get_result_columns()
        average_score, average_cost, total_cost, total_usage = self.save_results_to_csv(results, columns)
        logger.info(f"Average score on {self.name} dataset: {average_score:.5f}")
        logger.info(f"Total Cost: {total_cost:.5f}")
        for role, ru in total_usage.items():
            logger.info(f"Usage ({role}): {ru['total_input_tokens']} input + {ru['total_output_tokens']} output tokens")
        return average_score, average_cost, total_cost, total_usage

    async def run_baseline(self, agent: Callable, max_concurrent_tasks: int = 50):
        data = await self.load_data()
        results = await self.evaluate_all_problems(data, agent, max_concurrent_tasks)
        columns = self.get_result_columns()
        average_score, average_cost, total_cost, total_usage = self.save_results_to_csv(results, columns)
        logger.info(f"Average score on {self.name} dataset: {average_score:.5f}")
        logger.info(f"Total Cost: {total_cost:.5f}")
        logger.info(f"Avg Cost:{average_cost:.5f}")
        return average_score, average_cost, total_cost, total_usage

