"""Contains the different parser functions for the experiment"""

import argparse

from models import DATASET_DEFAULTS


def get_search_args() -> argparse.Namespace:
    """Get the arguments for the search experiment

    Returns:
        argparse.Namespace: The arguments for the search experiment
    """
    parser = argparse.ArgumentParser(description="Search for the best agentic design")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(DATASET_DEFAULTS.keys()),
        required=True,
        help="Dataset to run the experiment on.",
    )
    parser.add_argument(
        "--exp_results_dir",
        type=str,
        default=None,
        help="Directory to save the experiment results, if not provided, will use the default directory in the .env file.",
    )
    parser.add_argument(
        "--wandb_project",
        type=str,
        default=None,
        help="W&B project name. If set, enables Weights & Biases logging to this project (requires the `wandb` package). Off by default.",
    )
    parser.add_argument(
        "--weave",
        action="store_true",
        default=False,
        help="Enable Weave tracing (requires the `weave` package). Off by default.",
    )
    parser.add_argument(
        "--run_ndx", type=int, default=0, help="Run index, used to separate executions of the same configuration."
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for puzzle sampling.")
    parser.add_argument(
        "--bundle_id",
        type=int,
        default=None,
        help="Bundle index to use from data/bundles/<puzzle>/seed_<seed>/<bundle_id>/. If not set, uses default dataset files.",
    )
    parser.add_argument("--sample", type=int, default=4, help="Sample count for optimization.")
    parser.add_argument("--max_rounds", type=int, default=20, help="Max optimization rounds.")
    parser.add_argument(
        "--validation_rounds", type=int, default=1, help="Number of validation rounds per optimization step."
    )
    parser.add_argument(
        "--opt_model_name",
        type=str,
        default="gpt-5.4-mini",
        help="Model for the AFlow graph optimizer.",
    )
    parser.add_argument(
        "--opt_temperature",
        type=float,
        required=True,
        help="Temperature for the optimizer model. Required — no default.",
    )
    parser.add_argument(
        "--aggregator_model",
        type=str,
        default="gpt-5.4-mini",
        help="Model for the aggregator/coordinator role in MAS operators.",
    )
    parser.add_argument(
        "--aggregator_temperature",
        type=float,
        required=True,
        help="Temperature for the aggregator model. Required — no default.",
    )
    parser.add_argument(
        "--worker_model",
        type=str,
        default="gpt-5.4-mini",
        help="Model for the worker role in MAS operators.",
    )
    parser.add_argument(
        "--worker_temperature",
        type=float,
        required=True,
        help="Temperature for the worker model. Required — no default.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Wipe the experiment folder before running if it already exists.",
    )
    parser.add_argument(
        "--max_calls_per_workflow",
        type=int,
        default=20,
        help=(
            "Per-puzzle LLM call budget. A workflow that makes more than this "
            "many AsyncLLM calls on a single puzzle is killed and reports a "
            "[CALL_BUDGET_EXCEEDED] feedback string as its prediction. "
            "Default: 20. Pass 0 or a negative value to disable."
        ),
    )
    return parser.parse_args()
