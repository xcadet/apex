from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.sudoku.verifier import verify


class EnigmataSudokuBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
