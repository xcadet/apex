from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.campsite.verifier import verify


class EnigmataCampsiteBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
