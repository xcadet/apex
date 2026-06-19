# -*- coding: utf-8 -*-
# @Date    : 8/12/2024 22:00 PM
# @Author  : issac
# @Desc    : optimizer for graph (updated with AsyncLLM integration)

import asyncio
import os
import sys
import time
from typing import List, Literal, Dict

from pydantic import BaseModel, Field

from scripts.evaluator import DatasetType
# call_tracking lives in the repo root and is on sys.path because search.py
# inserts the repo dir before launching. Imported lazily-friendly: if it's
# missing (e.g. running raw aflow tests), the contextvar setters become
# no-ops.
try:
    from call_tracking import set_round, set_phase  # type: ignore
except ImportError:  # pragma: no cover - aflow standalone fallback
    def set_round(*_a, **_kw):
        from contextlib import nullcontext
        return nullcontext()
    def set_phase(*_a, **_kw):
        from contextlib import nullcontext
        return nullcontext()
from scripts.optimizer_utils.convergence_utils import ConvergenceUtils
from scripts.optimizer_utils.data_utils import DataUtils
from scripts.optimizer_utils.evaluation_utils import EvaluationUtils
from scripts.optimizer_utils.experience_utils import ExperienceUtils
from scripts.optimizer_utils.graph_utils import GraphUtils
from scripts.formatter import XmlFormatter, FormatError
from scripts.logs import logger

QuestionType = Literal["math", "code", "qa"]
OptimizerType = Literal["Graph", "Test"]


class GraphOptimize(BaseModel):
    modification: str = Field(default="", description="modification")
    graph: str = Field(default="", description="graph")
    prompt: str = Field(default="", description="prompt")


class Optimizer:
    def __init__(
        self,
        dataset: DatasetType,
        question_type: QuestionType,
        operators: List,
        sample: int,
        role_llms: dict,
        check_convergence: bool = False,
        optimized_path: str = None,
        initial_round: int = 1,
        max_rounds: int = 20,
        validation_rounds: int = 5,
        puzzle_specs: dict = None,
    ) -> None:
        self.role_llms = role_llms
        self.optimize_llm = role_llms["optimizer"]
        self.execute_llm_config = role_llms["worker"].config
        self.aggregator_llm_config = role_llms["aggregator"].config

        self.dataset = dataset
        self.type = question_type
        self.check_convergence = check_convergence
        self.puzzle_specs = puzzle_specs or {}

        self.graph = None
        self.operators = operators

        self.root_path = f"{optimized_path}/{self.dataset}"
        self.sample = sample
        self.top_scores = []
        self.round = initial_round
        self.max_rounds = max_rounds
        self.validation_rounds = validation_rounds

        # Add the experiment output dir to sys.path so generated graphs are importable
        # as {dataset}.workflows.round_{N}.graph
        abs_optimized_path = os.path.abspath(optimized_path)
        if abs_optimized_path not in sys.path:
            sys.path.insert(0, abs_optimized_path)

        self.graph_utils = GraphUtils(self.root_path, self.dataset)
        self.data_utils = DataUtils(self.root_path)
        self.experience_utils = ExperienceUtils(self.root_path)
        self.evaluation_utils = EvaluationUtils(self.root_path)
        self.convergence_utils = ConvergenceUtils(self.root_path)

    def optimize(self, mode: OptimizerType = "Graph"):
        if mode == "Test":
            test_n = 1  # validation datasets's execution number
            for i in range(test_n):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                score = loop.run_until_complete(self.test())
            return None

        best_score = None
        self.round_metrics = []
        self.optimizer_traces = []
        self.initial_round_metrics = None
        prev_opt_usage = self.optimize_llm.get_usage_summary()
        for opt_round in range(self.max_rounds):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            retry_count = 0
            max_retries = 1

            while retry_count < max_retries:
                try:
                    score, exec_usage = loop.run_until_complete(self._optimize_graph())
                    break
                except Exception as e:
                    retry_count += 1
                    logger.info(f"Error occurred: {e}. Retrying... (Attempt {retry_count}/{max_retries})")
                    if retry_count == max_retries:
                        logger.info("Max retries reached. Moving to next round.")
                        score = None
                        exec_usage = {}

                    wait_time = 5 * retry_count
                    time.sleep(wait_time)

                if retry_count < max_retries:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

            self.round += 1

            # Compute optimizer LLM token delta for this round
            cur_opt_usage = self.optimize_llm.get_usage_summary()
            opt_input_delta = cur_opt_usage["total_input_tokens"] - prev_opt_usage["total_input_tokens"]
            opt_output_delta = cur_opt_usage["total_output_tokens"] - prev_opt_usage["total_output_tokens"]
            prev_opt_usage = cur_opt_usage

            logger.info(f"Score for round {self.round}: {score}")

            # Collect round metrics (always — tokens were spent even if evaluation failed)
            if score is not None and (best_score is None or score > best_score):
                best_score = score
            worker_usage = exec_usage.get("worker", {}) if isinstance(exec_usage, dict) else {}
            aggregator_usage = exec_usage.get("aggregator", {}) if isinstance(exec_usage, dict) else {}
            self.round_metrics.append({
                "round": self.round,
                "val_score": score,
                "best_val_score": best_score,
                # Optimizer LLM (graph code generation) — this round only
                "optimizer_input_tokens": opt_input_delta,
                "optimizer_output_tokens": opt_output_delta,
                "optimizer_cumul_input_tokens": cur_opt_usage["total_input_tokens"],
                "optimizer_cumul_output_tokens": cur_opt_usage["total_output_tokens"],
                # Worker LLM (graph evaluation) — this round only
                "worker_input_tokens": worker_usage.get("total_input_tokens", 0),
                "worker_output_tokens": worker_usage.get("total_output_tokens", 0),
                # Aggregator LLM (graph evaluation) — this round only
                "aggregator_input_tokens": aggregator_usage.get("total_input_tokens", 0),
                "aggregator_output_tokens": aggregator_usage.get("total_output_tokens", 0),
            })

            converged, convergence_round, final_round = self.convergence_utils.check_convergence(top_k=3)

            if converged and self.check_convergence:
                logger.info(
                    f"Convergence detected, occurred in round {convergence_round}, final round is {final_round}"
                )
                self.convergence_utils.print_results()
                break

            time.sleep(5)

        self.best_score = best_score

    async def _optimize_graph(self):
        validation_n = self.validation_rounds  # validation datasets's execution number
        graph_path = f"{self.root_path}/workflows"
        data = self.data_utils.load_results(graph_path)

        if self.round == 1:
            directory = self.graph_utils.create_round_directory(graph_path, self.round)
            # Load graph using graph_utils
            self.graph = self.graph_utils.load_graph(self.round, graph_path)
            with set_round(self.round), set_phase("evaluate_initial"):
                avg_score, initial_usage = await self.evaluation_utils.evaluate_graph(self, directory, validation_n, data, initial=True)
            # Record round 1 (seed graph) metrics
            init_worker = initial_usage.get("worker", {})
            init_aggregator = initial_usage.get("aggregator", {})
            self.initial_round_metrics = {
                "round": 1,
                "val_score": avg_score,
                "worker_input_tokens": init_worker.get("total_input_tokens", 0),
                "worker_output_tokens": init_worker.get("total_output_tokens", 0),
                "aggregator_input_tokens": init_aggregator.get("total_input_tokens", 0),
                "aggregator_output_tokens": init_aggregator.get("total_output_tokens", 0),
            }

        # Create a loop until the generated graph meets the check conditions
        while True:
            directory = self.graph_utils.create_round_directory(graph_path, self.round + 1)

            top_rounds = self.data_utils.get_top_rounds(self.sample)
            sample = self.data_utils.select_round(top_rounds)

            prompt, graph_load = self.graph_utils.read_graph_files(sample["round"], graph_path)
            graph = self.graph_utils.extract_solve_graph(graph_load)

            processed_experience = self.experience_utils.load_experience()
            experience = self.experience_utils.format_experience(processed_experience, sample["round"])

            operator_description = self.graph_utils.load_operators_description(self.operators)
            log_data = self.data_utils.load_log(sample["round"])

            graph_optimize_prompt = self.graph_utils.create_graph_optimize_prompt(
                experience, sample["score"], graph[0], prompt, operator_description, self.type, log_data
            )

            # Replace ActionNode with AsyncLLM and XmlFormatter
            raw_response_text = None
            try:
                graph_formatter = XmlFormatter.from_model(GraphOptimize)
                with set_round(self.round + 1), set_phase("graph_optimize"):
                    response = await self.optimize_llm.call_with_format(
                        graph_optimize_prompt,
                        graph_formatter
                    )
                raw_response_text = str(response)
                logger.info(f"Graph optimization response received successfully")
            except FormatError as e:
                logger.error(f"Format error in graph optimization: {str(e)}")
                with set_round(self.round + 1), set_phase("graph_optimize_retry"):
                    raw_response_text = await self.optimize_llm(graph_optimize_prompt)
                response = self._extract_fields_from_response(raw_response_text)
                if not response:
                    logger.error("Failed to extract fields from raw response, retrying...")
                    self.optimizer_traces.append({
                        "round": self.round + 1,
                        "prompt": graph_optimize_prompt,
                        "response": raw_response_text,
                        "accepted": False,
                    })
                    continue

            check = self.experience_utils.check_modification(
                processed_experience, response["modification"], sample["round"]
            )

            self.optimizer_traces.append({
                "round": self.round + 1,
                "prompt": graph_optimize_prompt,
                "response": raw_response_text,
                "accepted": check,
            })

            if check:
                break

        # Save the graph and evaluate
        self.graph_utils.write_graph_files(directory, response, self.round + 1, self.dataset)

        experience = self.experience_utils.create_experience_data(sample, response["modification"])

        self.graph = self.graph_utils.load_graph(self.round + 1, graph_path)

        logger.info(directory)

        with set_round(self.round + 1), set_phase("evaluate"):
            avg_score, round_usage = await self.evaluation_utils.evaluate_graph(self, directory, validation_n, data, initial=False)

        self.experience_utils.update_experience(directory, experience, avg_score)

        return avg_score, round_usage

    def _extract_fields_from_response(self, response: str) -> Dict[str, str]:
        """
        Fallback method to extract fields from raw response text using basic parsing
        
        Args:
            response: Raw response text from LLM
            
        Returns:
            Dictionary with extracted fields or None if extraction fails
        """
        try:
            # Try to extract XML tags with regex
            import re
            
            # Initialize result dictionary with default values
            result = {
                "modification": "",
                "graph": "",
                "prompt": ""
            }
            
            # Extract each field with regex
            for field in result.keys():
                pattern = rf"<{field}>(.*?)</{field}>"
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    result[field] = match.group(1).strip()
            
            # Verify we have at least some content
            if not any(result.values()):
                logger.error("No fields could be extracted from response")
                return None
            
            return result
        except Exception as e:
            logger.error(f"Error extracting fields from response: {str(e)}")
            return None

    async def test(self):
        rounds = [1]  # You can choose the rounds you want to test here.
        data = []

        graph_path = f"{self.root_path}/workflows_test"
        json_file_path = self.data_utils.get_results_file_path(graph_path)

        data = self.data_utils.load_results(graph_path)

        for round in rounds:
            directory = self.graph_utils.create_round_directory(graph_path, round)
            self.graph = self.graph_utils.load_graph(round, graph_path)

            score, avg_cost, total_cost = await self.evaluation_utils.evaluate_graph_test(self, directory, is_test=True)

            new_data = self.data_utils.create_result_data(round, score, avg_cost, total_cost)
            data.append(new_data)

            self.data_utils.save_results(json_file_path, data)