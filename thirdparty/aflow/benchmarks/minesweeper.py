from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.minesweeper.verifier import verify


class EnigmataMinesweeperBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
