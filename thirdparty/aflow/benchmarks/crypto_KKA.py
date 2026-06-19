from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.crypto_KKA.verifier import verify


class EnigmataCryptoKKABenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
