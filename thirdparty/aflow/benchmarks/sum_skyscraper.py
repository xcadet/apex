from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.sum_skyscraper.verifier import verify


class EnigmataSumSkyscraperBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
