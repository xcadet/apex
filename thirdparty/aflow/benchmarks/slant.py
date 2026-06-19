from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.slant.verifier import verify


class EnigmataSlantBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
