from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.skyscraper.verifier import verify


class EnigmataSkyscraperBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
