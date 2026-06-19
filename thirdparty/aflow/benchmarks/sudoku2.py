from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.sudoku2.verifier import verify


class EnigmataSudoku2Benchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
