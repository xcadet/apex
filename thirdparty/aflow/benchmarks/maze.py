from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.maze.verifier import verify


class EnigmataMazeBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
