# -*- coding: utf-8 -*-
# @Date    : 8/23/2024 10:00 AM
# @Author  : all
# @Desc    : Evaluation for different datasets

from typing import Dict, Literal, Tuple

# Dataset (CamelCase, as used by AFlow / our DATASET_DEFAULTS) → puzzle name
# (snake_case, as used by the on-disk bundle directory layout). Source of
# truth for resolving data/<puzzle_name>/bundles/<id>/{train,test}.jsonl.
_ENIGMATA_DATASET_TO_PUZZLE_NAME: dict = {
    "EnigmataBinario": "binario",
    "EnigmataCampsite": "campsite",
    "EnigmataCarPainting": "car_painting",
    "EnigmataCountdown": "countdown",
    "EnigmataCryptoKKA": "crypto_KKA",
    "EnigmataCryptoKPA": "crypto_KPA",
    "EnigmataGame24": "game24",
    "EnigmataHamiltonianCycle": "hamiltonian_cycle",
    "EnigmataHamiltonianPath": "hamiltonian_path",
    "EnigmataHitori": "hitori",
    "EnigmataKakurasu": "kakurasu",
    "EnigmataLightUp": "light_up",
    "EnigmataMagicSquare": "magic_square",
    "EnigmataMaze": "maze",
    "EnigmataMinesweeper": "minesweeper",
    "EnigmataNaturalLanguageNavigation": "natural_language_navigation",
    "EnigmataSkyscraper": "skyscraper",
    "EnigmataSlant": "slant",
    "EnigmataStackPermutation": "stack_permutation",
    "EnigmataStarBattle": "star_battle",
    "EnigmataSudoku": "sudoku",
    "EnigmataSudoku2": "sudoku2",
    "EnigmataSumSkyscraper": "sum_skyscraper",
    "EnigmataTicTacToe": "tic_tac_toe",
    "EnigmataTwiddle": "twiddle",
    "EnigmataZebraLogic": "zebra_logic",
}

from benchmarks.benchmark import BaseBenchmark
from benchmarks.drop import DROPBenchmark
from benchmarks.gsm8k import GSM8KBenchmark
from benchmarks.hotpotqa import HotpotQABenchmark
from benchmarks.humaneval import HumanEvalBenchmark
from benchmarks.math import MATHBenchmark
from benchmarks.mbpp import MBPPBenchmark
from benchmarks.livecodebench import LiveCodeBench
from benchmarks.zebra_logic import EnigmataZebraLogicBenchmark
from benchmarks.binario import EnigmataBinarioBenchmark
from benchmarks.campsite import EnigmataCampsiteBenchmark
from benchmarks.car_painting import EnigmataCarPaintingBenchmark
from benchmarks.countdown import EnigmataCountdownBenchmark
from benchmarks.crypto_KKA import EnigmataCryptoKKABenchmark
from benchmarks.crypto_KPA import EnigmataCryptoKPABenchmark
from benchmarks.game24 import EnigmataGame24Benchmark
from benchmarks.hamiltonian_cycle import EnigmataHamiltonianCycleBenchmark
from benchmarks.hamiltonian_path import EnigmataHamiltonianPathBenchmark
from benchmarks.hitori import EnigmataHitoriBenchmark
from benchmarks.kakurasu import EnigmataKakurasuBenchmark
from benchmarks.light_up import EnigmataLightUpBenchmark
from benchmarks.magic_square import EnigmataMagicSquareBenchmark
from benchmarks.maze import EnigmataMazeBenchmark
from benchmarks.minesweeper import EnigmataMinesweeperBenchmark
from benchmarks.natural_language_navigation import EnigmataNaturalLanguageNavigationBenchmark
from benchmarks.skyscraper import EnigmataSkyscraperBenchmark
from benchmarks.slant import EnigmataSlantBenchmark
from benchmarks.stack_permutation import EnigmataStackPermutationBenchmark
from benchmarks.star_battle import EnigmataStarBattleBenchmark
from benchmarks.sudoku import EnigmataSudokuBenchmark
from benchmarks.sudoku2 import EnigmataSudoku2Benchmark
from benchmarks.sum_skyscraper import EnigmataSumSkyscraperBenchmark
from benchmarks.tic_tac_toe import EnigmataTicTacToeBenchmark
from benchmarks.twiddle import EnigmataTwiddleBenchmark

# If you want to customize tasks, add task types here and provide evaluation functions, just like the ones given above
DatasetType = Literal[
    "HumanEval", "MBPP", "GSM8K", "MATH", "HotpotQA", "DROP", "LiveCodeBench",
    "EnigmataZebraLogic",
    "EnigmataBinario",
    "EnigmataCampsite",
    "EnigmataCarPainting",
    "EnigmataCountdown",
    "EnigmataCryptoKKA",
    "EnigmataCryptoKPA",
    "EnigmataGame24",
    "EnigmataHamiltonianCycle",
    "EnigmataHamiltonianPath",
    "EnigmataHitori",
    "EnigmataKakurasu",
    "EnigmataLightUp",
    "EnigmataMagicSquare",
    "EnigmataMaze",
    "EnigmataMinesweeper",
    "EnigmataNaturalLanguageNavigation",
    "EnigmataSkyscraper",
    "EnigmataSlant",
    "EnigmataStackPermutation",
    "EnigmataStarBattle",
    "EnigmataSudoku",
    "EnigmataSudoku2",
    "EnigmataSumSkyscraper",
    "EnigmataTicTacToe",
    "EnigmataTwiddle",
]


class Evaluator:
    """
    Complete the evaluation for different datasets here
    """

    def __init__(self, eval_path: str):
        self.eval_path = eval_path
        self.dataset_configs: Dict[DatasetType, BaseBenchmark] = {
            "GSM8K": GSM8KBenchmark,
            "MATH": MATHBenchmark,
            "HumanEval": HumanEvalBenchmark,
            "HotpotQA": HotpotQABenchmark,
            "MBPP": MBPPBenchmark,
            "DROP": DROPBenchmark,
            "LiveCodeBench": LiveCodeBench,
            "EnigmataZebraLogic": EnigmataZebraLogicBenchmark,
            "EnigmataBinario": EnigmataBinarioBenchmark,
            "EnigmataCampsite": EnigmataCampsiteBenchmark,
            "EnigmataCarPainting": EnigmataCarPaintingBenchmark,
            "EnigmataCountdown": EnigmataCountdownBenchmark,
            "EnigmataCryptoKKA": EnigmataCryptoKKABenchmark,
            "EnigmataCryptoKPA": EnigmataCryptoKPABenchmark,
            "EnigmataGame24": EnigmataGame24Benchmark,
            "EnigmataHamiltonianCycle": EnigmataHamiltonianCycleBenchmark,
            "EnigmataHamiltonianPath": EnigmataHamiltonianPathBenchmark,
            "EnigmataHitori": EnigmataHitoriBenchmark,
            "EnigmataKakurasu": EnigmataKakurasuBenchmark,
            "EnigmataLightUp": EnigmataLightUpBenchmark,
            "EnigmataMagicSquare": EnigmataMagicSquareBenchmark,
            "EnigmataMaze": EnigmataMazeBenchmark,
            "EnigmataMinesweeper": EnigmataMinesweeperBenchmark,
            "EnigmataNaturalLanguageNavigation": EnigmataNaturalLanguageNavigationBenchmark,
            "EnigmataSkyscraper": EnigmataSkyscraperBenchmark,
            "EnigmataSlant": EnigmataSlantBenchmark,
            "EnigmataStackPermutation": EnigmataStackPermutationBenchmark,
            "EnigmataStarBattle": EnigmataStarBattleBenchmark,
            "EnigmataSudoku": EnigmataSudokuBenchmark,
            "EnigmataSudoku2": EnigmataSudoku2Benchmark,
            "EnigmataSumSkyscraper": EnigmataSumSkyscraperBenchmark,
            "EnigmataTicTacToe": EnigmataTicTacToeBenchmark,
            "EnigmataTwiddle": EnigmataTwiddleBenchmark,
        }

    async def graph_evaluate(
        self, dataset: DatasetType, graph, params: dict, path: str, is_test: bool = False
    ) -> Tuple[float, float, float, dict]:
        if dataset not in self.dataset_configs:
            raise ValueError(f"Unsupported dataset: {dataset}")

        benchmark_class = self.dataset_configs[dataset]
        puzzle_specs = params.get("puzzle_specs")
        data_path = self._get_data_path(dataset, is_test, puzzle_specs=puzzle_specs)
        # Pass puzzle_specs to benchmarks that accept it (e.g. EnigmataBenchmark subclasses)
        try:
            benchmark = benchmark_class(name=dataset, file_path=data_path, log_path=path, puzzle_specs=puzzle_specs)
        except TypeError:
            benchmark = benchmark_class(name=dataset, file_path=data_path, log_path=path)

        # Use params to configure the graph and benchmark
        configured_graph = await self._configure_graph(dataset, graph, params)
        if is_test:
            va_list = None  # For test data, generally use None to test all
        else:
            va_list = None  # Use None to test all Validation data, or set va_list (e.g., [1, 2, 3]) to use partial data
        return await benchmark.run_evaluation(configured_graph, va_list)

    async def _configure_graph(self, dataset, graph, params: dict):
        dataset_config = params.get("dataset", {})
        llm_config = params.get("llm_config", {})
        aggregator_llm_config = params.get("aggregator_llm_config", {})
        return graph(
            name=dataset,
            llm_config=llm_config,
            dataset=dataset_config,
            aggregator_llm_config=aggregator_llm_config,
        )

    def _get_data_path(self, dataset: DatasetType, test: bool, puzzle_specs: dict = None) -> str:
        import os
        puzzle_specs = puzzle_specs or {}
        bundle_id = puzzle_specs.get("bundle_id")

        # If a bundle_id is provided, resolve from the bundle directory.
        # Layout on disk: data/<puzzle_name>/bundles/<bundle_id>/{train,test}.jsonl
        # The bundles only ship train + test; AFlow's "validate" split (used
        # during optimization rounds when is_test=False) is served from train.jsonl.
        if bundle_id is not None:
            puzzle_name = _ENIGMATA_DATASET_TO_PUZZLE_NAME.get(dataset, dataset.lower())
            filename = "test.jsonl" if test else "train.jsonl"
            for prefix in ["", "aflow/"]:
                candidate = os.path.join(prefix, "data", puzzle_name, "bundles", str(bundle_id), filename)
                if os.path.exists(candidate):
                    return candidate
            # Fall back to expected path for clear error message
            return os.path.join("data", puzzle_name, "bundles", str(bundle_id), filename)

        # Default: load from data/datasets/
        for prefix in ["", "aflow/"]:
            base_path = f"{prefix}data/datasets/{dataset.lower()}"
            candidate = f"{base_path}_test.jsonl" if test else f"{base_path}_validate.jsonl"
            if os.path.exists(candidate):
                return candidate
        # Fall back to the original relative path
        base_path = f"data/datasets/{dataset.lower()}"
        return f"{base_path}_test.jsonl" if test else f"{base_path}_validate.jsonl"
