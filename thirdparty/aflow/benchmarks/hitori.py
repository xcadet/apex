from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.hitori.verifier import verify


class EnigmataHitoriBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
