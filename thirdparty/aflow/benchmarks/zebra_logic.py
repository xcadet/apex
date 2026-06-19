from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.zebra_logic.verifier import verify


class EnigmataZebraLogicBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
