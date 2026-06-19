from benchmarks.enigmata import EnigmataBenchmark
from enigmata.verifiable_tasks.tasks.hamiltonian_path.verifier import verify


class EnigmataHamiltonianPathBenchmark(EnigmataBenchmark):
    def _verify(self, prediction: str, answer: str, meta: str) -> int:
        return verify(prediction, answer, meta)
