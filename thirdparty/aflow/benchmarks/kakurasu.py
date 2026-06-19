from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.kakurasu.verifier import verify


class EnigmataKakurasuBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
