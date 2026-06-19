from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.stack_permutation.verifier import verify


class EnigmataStackPermutationBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
