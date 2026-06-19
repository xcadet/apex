from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.countdown.verifier import verify


class EnigmataCountdownBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
