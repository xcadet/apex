from scripts.evaluator import Evaluator

try:
    from call_tracking import set_validation_repeat  # type: ignore
except ImportError:  # pragma: no cover
    def set_validation_repeat(*_a, **_kw):
        from contextlib import nullcontext
        return nullcontext()


class EvaluationUtils:
    def __init__(self, root_path: str):
        self.root_path = root_path

    async def evaluate_initial_round(self, optimizer, graph_path, directory, validation_n, data):
        # Load graph with graph_utils from optimizer
        optimizer.graph = optimizer.graph_utils.load_graph(optimizer.round, graph_path)
        evaluator = Evaluator(eval_path=directory)

        for i in range(validation_n):
            with set_validation_repeat(i):
                score, avg_cost, total_cost, total_usage = await evaluator.graph_evaluate(
                    optimizer.dataset,
                    optimizer.graph,
                    {"dataset": optimizer.dataset, "llm_config": optimizer.execute_llm_config, "aggregator_llm_config": optimizer.aggregator_llm_config, "puzzle_specs": optimizer.puzzle_specs},
                    directory,
                    is_test=False,
                )

            new_data = optimizer.data_utils.create_result_data(optimizer.round, score, avg_cost, total_cost, usage=total_usage)
            data.append(new_data)

            result_path = optimizer.data_utils.get_results_file_path(graph_path)
            optimizer.data_utils.save_results(result_path, data)

        return data

    async def evaluate_graph(self, optimizer, directory, validation_n, data, initial=False):
        evaluator = Evaluator(eval_path=directory)
        sum_score = 0
        _empty_role = {"total_input_tokens": 0, "total_output_tokens": 0, "total_cost": 0.0}
        sum_usage = {"worker": dict(_empty_role), "aggregator": dict(_empty_role)}

        for i in range(validation_n):
            with set_validation_repeat(i):
                score, avg_cost, total_cost, total_usage = await evaluator.graph_evaluate(
                    optimizer.dataset,
                    optimizer.graph,
                    {"dataset": optimizer.dataset, "llm_config": optimizer.execute_llm_config, "aggregator_llm_config": optimizer.aggregator_llm_config, "puzzle_specs": optimizer.puzzle_specs},
                    directory,
                    is_test=False,
                )

            cur_round = optimizer.round + 1 if initial is False else optimizer.round

            new_data = optimizer.data_utils.create_result_data(cur_round, score, avg_cost, total_cost, usage=total_usage)
            data.append(new_data)

            result_path = optimizer.data_utils.get_results_file_path(f"{optimizer.root_path}/workflows")
            optimizer.data_utils.save_results(result_path, data)

            sum_score += score
            for role in sum_usage:
                role_usage = total_usage.get(role, {})
                for k in sum_usage[role]:
                    sum_usage[role][k] += role_usage.get(k, 0)

        avg_score = sum_score / validation_n
        return avg_score, sum_usage

    async def evaluate_graph_test(self, optimizer, directory, is_test=True):
        evaluator = Evaluator(eval_path=directory)
        return await evaluator.graph_evaluate(
            optimizer.dataset,
            optimizer.graph,
            {"dataset": optimizer.dataset, "llm_config": optimizer.execute_llm_config, "aggregator_llm_config": optimizer.aggregator_llm_config, "puzzle_specs": optimizer.puzzle_specs},
            directory,
            is_test=is_test,
        )
