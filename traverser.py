import json
import os
import shutil

from scripts.optimizer import Optimizer
from models import ExperimentConfig, AflowOptimizerType
from operators.factory import build_role_llms


class Traverser:
    def __init__(self, experiment_config: ExperimentConfig, args=None):
        self.args = args


class AFlowTraverser(Traverser):
    # Canonical workspace templates live here (relative to repo root)
    WORKSPACE_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "thirdparty", "aflow", "workspace")

    def __init__(self, experiment_config: ExperimentConfig, args=None):
        super().__init__(experiment_config, args)

    def traverse(self, experiment_config: ExperimentConfig) -> None:
        dataset = experiment_config.puzzle_specs.dataset
        question_type = experiment_config.puzzle_specs.question_type
        operators = experiment_config.agentic_design_specs.operators

        # Build per-role LLM instances from the sweep config
        role_llms = build_role_llms(experiment_config.agentic_design_specs)

        optimized_path = os.path.join(self.args.exp_results_dir, self.args.experiment_id)
        overwrite = self.args.overwrite
        self._prepare_experiment_dir(optimized_path, overwrite)

        # Initialize the experiment workspace
        self._init_experiment_workspace(optimized_path, dataset)

        optimizer = Optimizer(
            dataset=dataset,
            question_type=question_type,
            operators=operators,
            sample=self.args.sample,
            role_llms=role_llms,
            max_rounds=self.args.max_rounds,
            validation_rounds=self.args.validation_rounds,
            optimized_path=optimized_path,
            puzzle_specs=experiment_config.puzzle_specs.model_dump(),
        )
        optimizer.optimize(AflowOptimizerType.GRAPH)
        return optimizer

    @staticmethod
    def _prepare_experiment_dir(optimized_path: str, overwrite: bool) -> None:
        """Ensure the experiment directory is ready.

        Only raises if actual experiment data (a workflows/ subdirectory) exists
        and overwrite is False. An empty dir or one with only wandb files is fine.
        """
        # Check if any dataset workflows dir exists (sign of a previous run)
        has_experiment_data = (
            any(
                os.path.isdir(os.path.join(optimized_path, d, "workflows"))
                for d in os.listdir(optimized_path)
                if os.path.isdir(os.path.join(optimized_path, d))
            )
            if os.path.exists(optimized_path)
            else False
        )

        if has_experiment_data:
            if overwrite:
                shutil.rmtree(optimized_path, ignore_errors=True)
                if os.path.exists(optimized_path):
                    import subprocess

                    subprocess.run(["rm", "-rf", optimized_path], check=True)
            else:
                raise RuntimeError(
                    f"Experiment data already exists: {optimized_path}\nUse --overwrite to wipe it and start fresh."
                )

    def _init_experiment_workspace(self, optimized_path: str, dataset: str) -> None:
        """Set up a fresh experiment workspace from the canonical template.

        Creates the full directory structure the optimizer expects:
            {optimized_path}/{dataset}/workflows/
                template/   — operators, prompts, operator schema
                round_1/    — seed graph and prompt
                results.json
                processed_experience.json
        """
        root = os.path.join(optimized_path, dataset)
        workflows = os.path.join(root, "workflows")

        if os.path.exists(os.path.join(workflows, "template")):
            return  # Already initialized

        os.makedirs(workflows, exist_ok=True)

        self._setup_template(workflows, dataset)
        self._setup_initial_round(workflows, dataset)
        self._setup_results(workflows)
        self._ensure_packages(root)

    def _resolve_workspace_source(self, dataset: str) -> str:
        """Return the workspace source directory for the given dataset.

        Enigmata datasets use the shared _enigmata_base workspace.
        Other datasets use their own workspace directory.
        """
        if dataset.startswith("Enigmata"):
            return "_enigmata_base"
        return dataset

    def _setup_template(self, workflows_dir: str, dataset: str) -> None:
        """Copy operator definitions, prompts, and schema into workflows/template/."""
        source = self._resolve_workspace_source(dataset)
        src = os.path.join(self.WORKSPACE_TEMPLATE_DIR, source, "workflows", "template")
        dst = os.path.join(workflows_dir, "template")
        shutil.copytree(src, dst)
        self._rewrite_imports(dst, dataset, source=source)

    def _setup_initial_round(self, workflows_dir: str, dataset: str) -> None:
        """Copy the seed round_1 graph and prompt into the experiment workspace."""
        source = self._resolve_workspace_source(dataset)
        src = os.path.join(self.WORKSPACE_TEMPLATE_DIR, source, "workflows", "round_1")
        dst = os.path.join(workflows_dir, "round_1")
        shutil.copytree(src, dst)
        self._rewrite_imports(dst, dataset, source=source)

    def _setup_results(self, workflows_dir: str) -> None:
        """Create empty results.json and processed_experience.json."""
        for filename in ("results.json", "processed_experience.json"):
            path = os.path.join(workflows_dir, filename)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f)

    @staticmethod
    def _rewrite_imports(directory: str, dataset: str, source: str = None) -> None:
        """Rewrite workspace imports to be relative to the experiment dir.

        Replaces ``workspace.{source}.`` → ``{dataset}.`` in all .py files.
        """
        source = source or dataset
        old = f"workspace.{source}."
        new = f"{dataset}."
        for fname in os.listdir(directory):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(directory, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            updated = content.replace(old, new)
            if updated != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(updated)

    def _ensure_packages(self, root: str) -> None:
        """Create __init__.py at every directory level so the workspace is importable."""
        for dirpath, dirnames, filenames in os.walk(root):
            init_file = os.path.join(dirpath, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as _:
                    pass
