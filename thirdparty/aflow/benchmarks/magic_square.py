from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.magic_square.verifier import verify


class EnigmataMagicSquareBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
