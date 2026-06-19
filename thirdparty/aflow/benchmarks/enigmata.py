import json
from typing import Callable, Dict, List, Optional, Tuple

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed

# Best-effort import — when the call_tracking module is not on sys.path
# (e.g. running raw aflow tests outside the repo) we fall back to a sentinel
# class that nothing will ever isinstance() as, so the retry policy stays
# identical to the previous behavior.
try:
    from call_tracking import CallBudgetExceeded  # type: ignore
except ImportError:  # pragma: no cover
    class CallBudgetExceeded(Exception):  # type: ignore
        pass

from benchmarks.benchmark import BaseBenchmark
from scripts.logs import logger


class EnigmataBenchmark(BaseBenchmark):
    """Base benchmark for all Enigmata verifiable tasks.

    Subclasses must implement ``_verify`` to provide task-specific verification.
    """

    def __init__(self, name: str, file_path: str, log_path: str, puzzle_specs: Optional[Dict] = None):
        super().__init__(name, file_path, log_path)
        self.puzzle_specs = puzzle_specs or {}

    async def load_data(self, specific_indices: List[int] = None) -> List[dict]:
        data = await super().load_data(specific_indices)
        difficulty = self.puzzle_specs.get("difficulty")
        if difficulty is not None:
            data = [
                d for d in data
                if json.loads(d.get("meta", "{}")).get("difficulty_level") == difficulty
            ]
        return data

    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        """Return 1 if prediction is correct, 0 otherwise. Override in subclasses."""
        raise NotImplementedError

    def calculate_score(self, expected_output: str, prediction: str, meta: str) -> Tuple[float, str]:
        score = float(self._verify(prediction, expected_output, meta))
        return score, prediction

    # Retry every exception EXCEPT CallBudgetExceeded — a budget kill is a
    # deliberate verdict on the workflow, retrying it just wastes time
    # raising the same error 5×.
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(1),
        retry=retry_if_exception(lambda e: not isinstance(e, CallBudgetExceeded)),
        reraise=True,
    )
    async def _generate_output(self, graph, input_text):
        return await graph(input_text)

    async def evaluate_problem(self, problem: dict, graph: Callable) -> Tuple[str, str, str, float, dict]:
        input_text = problem["prompt"]
        expected_output = problem["answer"]
        meta = problem.get("meta", "{}")

        try:
            output, usage = await self._generate_output(graph, input_text)
            # usage is either a dict (full summary) or a float (legacy cost)
            if isinstance(usage, dict):
                cost = usage.get("total_cost", 0.0)
            else:
                cost = usage
                usage = {"total_cost": cost}
            score, extracted_output = self.calculate_score(expected_output, output, meta)

            if score < 1.0:
                self.log_mismatch(input_text, expected_output, output, extracted_output)

            return input_text, output, expected_output, score, usage

        except CallBudgetExceeded as e:
            # Substitute a clearly-labeled feedback string for the prediction.
            # This becomes the "output" the optimizer sees in next-round
            # log_data → it learns to generate graphs that make fewer LLM
            # calls per puzzle. The verifier will reject this string (it
            # isn't a valid puzzle answer), so score is 0 as expected.
            feedback = (
                f"[CALL_BUDGET_EXCEEDED] This workflow made {e.count} LLM "
                f"calls on a single puzzle, exceeding the per-puzzle budget "
                f"of {e.limit}. The execution was aborted to prevent runaway "
                f"cost. Redesign the graph to use fewer LLM calls per puzzle "
                f"(reduce loop iterations, drop redundant operators, prefer "
                f"single-shot prompts over multi-step debate when possible)."
            )
            logger.info(
                f"Workflow killed: call budget exceeded ({e.count}/{e.limit})."
            )
            return input_text, feedback, expected_output, 0.0, {"total_cost": 0.0}

        except Exception as e:
            logger.info(f"Maximum retries reached. Skipping this sample. Error: {e}")
            return input_text, str(e), expected_output, 0.0, {"total_cost": 0.0}

    def get_result_columns(self) -> List[str]:
        return ["inputs", "prediction", "expected_output", "score", "cost"]
