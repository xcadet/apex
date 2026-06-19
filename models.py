"""Defines the different models used in the project"""

from argparse import Namespace
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

Puzzles = List[str]

QuestionType = Literal["math", "code", "qa"]

_MAS_OPERATORS = ["Sequential", "Star", "SharedMemory", "Debate", "StarWithCoordinator", "DebateWithModerator"]

# Maps dataset names to their default question_type and operators
DATASET_DEFAULTS: Dict[str, Dict] = {
    "EnigmataZebraLogic": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataBinario": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataCampsite": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataCarPainting": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataCountdown": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataCryptoKKA": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataCryptoKPA": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataGame24": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataHamiltonianCycle": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataHamiltonianPath": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataHitori": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataKakurasu": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataLightUp": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataMagicSquare": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataMaze": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataMinesweeper": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataNaturalLanguageNavigation": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataSkyscraper": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataSlant": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataStackPermutation": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataStarBattle": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataSudoku": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataSudoku2": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataSumSkyscraper": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataTicTacToe": {"question_type": "qa", "operators": _MAS_OPERATORS},
    "EnigmataTwiddle": {"question_type": "qa", "operators": _MAS_OPERATORS},
}


class PuzzleSplit(str, Enum):
    """The data split of the puzzles"""

    TRAIN = "train"
    TEST = "test"


class AflowOptimizerType(str, Enum):
    """The optimizer mode from Aflow"""

    GRAPH = "Graph"
    TEST = "Test"


class ModelRoleConfig(BaseModel):
    """Model configuration for a specific role (optimizer, aggregator, worker)."""

    model_name: str
    temperature: float  # required — no default


class AgenticDesignSpecs(BaseModel):
    """The specifications of the agentic design"""

    operators: List[str]
    optimizer: ModelRoleConfig
    aggregator: ModelRoleConfig
    worker: ModelRoleConfig

    @classmethod
    def from_args(cls, args: Namespace) -> "AgenticDesignSpecs":
        defaults = DATASET_DEFAULTS[args.dataset]
        return cls(
            operators=defaults["operators"],
            optimizer=ModelRoleConfig(
                model_name=args.opt_model_name,
                temperature=args.opt_temperature,
            ),
            aggregator=ModelRoleConfig(
                model_name=getattr(args, "aggregator_model", args.opt_model_name),
                temperature=args.aggregator_temperature,
            ),
            worker=ModelRoleConfig(
                model_name=getattr(args, "worker_model", args.opt_model_name),
                temperature=args.worker_temperature,
            ),
        )


# Maps dataset names (CamelCase, as used in DATASET_DEFAULTS) to the short
# puzzle names (snake_case) used in the on-disk bundle directory layout:
#     data/<puzzle_name>/bundles/<bundle_id>/{train,test}.jsonl
DATASET_TO_PUZZLE_NAME: Dict[str, str] = {
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


class PuzzleSpecs(BaseModel):
    """The specifications of the puzzle"""

    seed: int  # Seed for the puzzle sample
    dataset: str
    question_type: QuestionType
    bundle_id: Optional[int] = None  # Bundle index under data/bundles/<puzzle>/seed_<seed>/<id>/

    @classmethod
    def from_args(cls, args: Namespace) -> "PuzzleSpecs":
        defaults = DATASET_DEFAULTS[args.dataset]
        return cls(
            seed=getattr(args, "seed", 42),
            dataset=args.dataset,
            question_type=defaults["question_type"],
            bundle_id=getattr(args, "bundle_id", None),
        )


class ExperimentConfig(BaseModel):
    """The configuration of the experiment"""

    agentic_design_specs: AgenticDesignSpecs  # Agentic Design Specifications
    puzzle_specs: PuzzleSpecs  # Puzzle Specifications
    run_ndx: int

    @classmethod
    def from_args(cls, args: Namespace) -> "ExperimentConfig":
        """Create an ExperimentConfig from the namespace arguments"""
        return cls(
            agentic_design_specs=AgenticDesignSpecs.from_args(args),
            puzzle_specs=PuzzleSpecs.from_args(args),
            run_ndx=args.run_ndx,
        )


class AgenticDesignConverter(BaseModel):
    """The converter of the agentic design, converts from the sweep to
    the agentic design space usable by the optimizer"""


class PuzzleSampler(BaseModel):
    """
    Given the puzzle specs, extract the puzzles from the puzzle space.
    """

    def __init__(self, puzzle_specs: PuzzleSpecs):
        """Initialize the puzzle sampler"""
        super().__init__()
        self.puzzle_specs = puzzle_specs
        self._puzzles = self._load_puzzles()

    def _load_puzzles(self) -> Dict[PuzzleSplit, Puzzles]:
        """Load the puzzles from the puzzle space"""
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def train_puzzles(self) -> List[Puzzles]:
        """Extract only the puzzles for the train split
        Returns:
            List[Puzzles]: The puzzles for the train split
        """
        return self._puzzles[PuzzleSplit.TRAIN]

    @property
    def test_puzzles(self) -> List[Puzzles]:
        """Extract only the puzzles for the test split

        Returns:
            List[Puzzles]: The puzzles for the test split
        """
        return self._puzzles[PuzzleSplit.TEST]
