from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.twiddle.verifier import verify


class EnigmataTwiddleBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
