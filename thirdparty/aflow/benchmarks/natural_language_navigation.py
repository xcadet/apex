from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.natural_language_navigation.verifier import verify


class EnigmataNaturalLanguageNavigationBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
