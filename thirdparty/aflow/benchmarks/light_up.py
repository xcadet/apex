from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.light_up.verifier import verify


class EnigmataLightUpBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
