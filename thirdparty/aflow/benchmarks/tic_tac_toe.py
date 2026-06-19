from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.tic_tac_toe.verifier import verify


class EnigmataTicTacToeBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
