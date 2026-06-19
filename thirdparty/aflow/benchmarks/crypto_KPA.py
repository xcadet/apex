from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.crypto_KPA.verifier import verify


class EnigmataCryptoKPABenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
