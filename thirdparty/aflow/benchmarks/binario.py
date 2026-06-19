from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.binario.verifier import verify


class EnigmataBinarioBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
