from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.car_painting.verifier import verify


class EnigmataCarPaintingBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
