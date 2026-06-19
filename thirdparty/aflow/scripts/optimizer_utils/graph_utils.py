import json
import os
import re
import sys
import time
import traceback
from typing import List

from scripts.prompts.optimize_prompt import (
    WORKFLOW_CUSTOM_USE,
    WORKFLOW_INPUT,
    WORKFLOW_OPTIMIZE_PROMPT,
    WORKFLOW_TEMPLATE,
    WORKFLOW_MAS_OPTIMIZE_PROMPT,
    WORKFLOW_MAS_USE,
    WORKFLOW_MAS_TEMPLATE,
)
from scripts.logs import logger


class GraphUtils:
    def __init__(self, root_path: str, dataset: str):
        self.root_path = root_path
        self.dataset = dataset

    def create_round_directory(self, graph_path: str, round_number: int) -> str:
        directory = os.path.join(graph_path, f"round_{round_number}")
        os.makedirs(directory, exist_ok=True)
        return directory

    def load_graph(self, round_number: int, workflows_path: str):
        graph_module_name = f"{self.dataset}.workflows.round_{round_number}.graph"

        # Invalidate all cached modules for this dataset so we always load the latest version
        for key in list(sys.modules.keys()):
            if key.startswith(f"{self.dataset}."):
                del sys.modules[key]

        try:
            graph_module = __import__(graph_module_name, fromlist=["Workflow"])
            graph_class = getattr(graph_module, "Workflow")
            return graph_class
        except ImportError as e:
            logger.error(f"Error loading graph for round {round_number}: {e}")
            raise

    def read_graph_files(self, round_number: int, workflows_path: str):
        prompt_file_path = os.path.join(workflows_path, f"round_{round_number}", "prompt.py")
        graph_file_path = os.path.join(workflows_path, f"round_{round_number}", "graph.py")

        try:
            with open(prompt_file_path, "r", encoding="utf-8") as file:
                prompt_content = file.read()
            with open(graph_file_path, "r", encoding="utf-8") as file:
                graph_content = file.read()
        except FileNotFoundError as e:
            logger.error(f"Error: File not found for round {round_number}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt for round {round_number}: {e}")
            raise
        return prompt_content, graph_content

    def extract_solve_graph(self, graph_load: str) -> List[str]:
        pattern = r"class Workflow:.+"
        return re.findall(pattern, graph_load, re.DOTALL)

    def load_operators_description(self, operators: List[str]) -> str:
        path = f"{self.root_path}/workflows/template/operator.json"
        operators_description = ""
        for id, operator in enumerate(operators):
            operator_description = self._load_operator_description(id + 1, operator, path)
            operators_description += f"{operator_description}\n"
        return operators_description

    def _load_operator_description(self, id: int, operator_name: str, file_path: str) -> str:
        with open(file_path, "r") as f:
            operator_data = json.load(f)
            matched_data = operator_data[operator_name]
            desc = matched_data["description"]
            interface = matched_data["interface"]
            return f"{id}. {operator_name}: {desc}, with interface {interface})."

    def create_graph_optimize_prompt(
        self,
        experience: str,
        score: float,
        graph: str,
        prompt: str,
        operator_description: str,
        type: str,
        log_data: str,
    ) -> str:
        graph_input = WORKFLOW_INPUT.format(
            experience=experience,
            score=score,
            graph=graph,
            prompt=prompt,
            operator_description=operator_description,
            type=type,
            log=log_data,
        )
        if self.dataset.startswith("Enigmata"):
            graph_system = WORKFLOW_MAS_OPTIMIZE_PROMPT.format(type=type)
            usage_prompt = WORKFLOW_MAS_USE
        else:
            graph_system = WORKFLOW_OPTIMIZE_PROMPT.format(type=type)
            usage_prompt = WORKFLOW_CUSTOM_USE
        return graph_input + usage_prompt + graph_system

    async def get_graph_optimize_response(self, graph_optimize_node):
        max_retries = 5
        retries = 0

        while retries < max_retries:
            try:
                response = graph_optimize_node.instruct_content.model_dump()
                return response
            except Exception as e:
                retries += 1
                logger.error(f"Error generating prediction: {e}. Retrying... ({retries}/{max_retries})")
                if retries == max_retries:
                    logger.info("Maximum retries reached. Skipping this sample.")
                    break
                traceback.print_exc()
                time.sleep(5)
        return None

    def write_graph_files(self, directory: str, response: dict, round_number: int, dataset: str):
        template = WORKFLOW_MAS_TEMPLATE if dataset.startswith("Enigmata") else WORKFLOW_TEMPLATE
        graph = template.format(graph=response["graph"], round=round_number, dataset=dataset)

        with open(os.path.join(directory, "graph.py"), "w", encoding="utf-8") as file:
            file.write(graph)

        with open(os.path.join(directory, "prompt.py"), "w", encoding="utf-8") as file:
            file.write(response["prompt"])

        with open(os.path.join(directory, "__init__.py"), "w", encoding="utf-8") as file:
            file.write("")
