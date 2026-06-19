#!/usr/bin/env python3
import os
import sys

# aflow internal imports assume aflow/ is on sys.path; the enigmata submodule
# is imported as a top-level `enigmata` package, so thirdparty/ must be too.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "thirdparty", "aflow"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "thirdparty"))


from dotenv import load_dotenv
from models import ExperimentConfig
from utils import generate_config_sha1
from exp_parser import get_search_args
from traverser import AFlowTraverser, Traverser
from call_tracking import install_call_tracking, set_workflow_call_limit


def generate_experiment_id(experiment_config: ExperimentConfig) -> str:
    return generate_config_sha1(experiment_config)


def run_experiment(experiment_config: ExperimentConfig, traverser: Traverser):
    return traverser.traverse(experiment_config)


if __name__ == "__main__":
    load_dotenv()
    args = get_search_args()
    experiment_config = ExperimentConfig.from_args(args)
    experiment_id = generate_experiment_id(experiment_config)
    args.experiment_id = experiment_id
    base_results_dir = args.exp_results_dir or os.environ.get("EXP_RESULTS_DIR", "apex_outputs")
    base_logs_dir = os.environ.get("EXP_LOGS_DIR", "apex_logs")
    args.exp_results_dir = os.path.join(base_results_dir, "searches")
    experiment_dir = os.path.join(args.exp_results_dir, experiment_id)
    logs_dir = os.path.join(base_logs_dir, "searches", experiment_id)
    traverser = AFlowTraverser(experiment_config, args)
    os.makedirs(experiment_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    call_log_path = os.path.join(logs_dir, "llm_calls.jsonl")
    call_tracker = install_call_tracking(call_log_path)

    _budget = args.max_calls_per_workflow
    set_workflow_call_limit(_budget if _budget is not None and _budget > 0 else None)
    run = None
    if args.wandb_project:
        import wandb

        run = wandb.init(
            project=args.wandb_project, name=experiment_id, dir=logs_dir, config=experiment_config.model_dump()
        )
    if args.weave:
        import weave

        weave.init(project_name=args.wandb_project or "apex", global_attributes={"experiment_id": experiment_id})

    import json

    metadata = {
        "experiment_id": experiment_id,
        "wandb_url": run.get_url() if run else None,
        "config": experiment_config.model_dump(),
        "results_dir": os.path.abspath(experiment_dir),
        "logs_dir": os.path.abspath(logs_dir),
    }
    with open(os.path.join(experiment_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    optimizer = run_experiment(experiment_config, traverser)

    # Collect all rounds: initial (seed graph) + optimization rounds
    all_rounds = []
    if optimizer.initial_round_metrics:
        all_rounds.append(optimizer.initial_round_metrics)
    all_rounds.extend(optimizer.round_metrics)

    cost_by_round_role: dict = {}
    calls_by_round_role: dict = {}
    for r in call_tracker.records:
        round_key = r.get("round")
        if round_key is None:
            continue
        role_key = r.get("role") or "unknown"
        cb = cost_by_round_role.setdefault(round_key, {})
        cb[role_key] = cb.get(role_key, 0.0) + (r.get("cost") or 0.0)
        nb = calls_by_round_role.setdefault(round_key, {})
        nb[role_key] = nb.get(role_key, 0) + 1

    for metrics in all_rounds:
        round_key = metrics["round"]
        per_role_cost = cost_by_round_role.get(round_key, {})
        per_role_n = calls_by_round_role.get(round_key, {})
        for role in ("optimizer", "worker", "aggregator"):
            metrics[f"{role}_cost"] = per_role_cost.get(role, 0.0)
            metrics[f"{role}_n_calls"] = per_role_n.get(role, 0)
        metrics["total_cost"] = sum(per_role_cost.values())
        metrics["n_calls"] = sum(per_role_n.values())

    cum_cost = 0.0
    cum_calls = 0
    cum_tokens = {role: {"in": 0, "out": 0} for role in ("optimizer", "worker", "aggregator")}
    for metrics in all_rounds:
        cum_cost += metrics.get("total_cost", 0.0)
        cum_calls += metrics.get("n_calls", 0)
        metrics["cumulative_cost"] = cum_cost
        metrics["cumulative_n_calls"] = cum_calls
        for role in ("optimizer", "worker", "aggregator"):
            cum_tokens[role]["in"] += metrics.get(f"{role}_input_tokens", 0)
            cum_tokens[role]["out"] += metrics.get(f"{role}_output_tokens", 0)
            metrics[f"{role}_cumulative_input_tokens"] = cum_tokens[role]["in"]
            metrics[f"{role}_cumulative_output_tokens"] = cum_tokens[role]["out"]

    if run:
        for metrics in all_rounds:
            wandb.log(metrics, step=metrics["round"])

    totals = {}
    for role in ("optimizer", "worker", "aggregator"):
        totals[f"{role}_in"] = sum(m.get(f"{role}_input_tokens", 0) for m in all_rounds)
        totals[f"{role}_out"] = sum(m.get(f"{role}_output_tokens", 0) for m in all_rounds)
        totals[f"{role}_cost"] = sum(m.get(f"{role}_cost", 0.0) for m in all_rounds)
        totals[f"{role}_n_calls"] = sum(m.get(f"{role}_n_calls", 0) for m in all_rounds)
        if run:
            wandb.run.summary[f"{role}_total_input_tokens"] = totals[f"{role}_in"]
            wandb.run.summary[f"{role}_total_output_tokens"] = totals[f"{role}_out"]
            wandb.run.summary[f"{role}_total_cost"] = totals[f"{role}_cost"]
            wandb.run.summary[f"{role}_total_calls"] = totals[f"{role}_n_calls"]

    total_cost = sum((r.get("cost") or 0.0) for r in call_tracker.records)
    total_calls = len(call_tracker.records)
    n_rounds_with_cost = max(len(all_rounds), 1)
    avg_cost_per_round = total_cost / n_rounds_with_cost
    avg_calls_per_round = total_calls / n_rounds_with_cost
    if run:
        unattributed_cost = total_cost - sum(
            totals[f"{role}_cost"] for role in ("optimizer", "worker", "aggregator")
        )
        unattributed_calls = total_calls - sum(
            totals[f"{role}_n_calls"] for role in ("optimizer", "worker", "aggregator")
        )
        wandb.run.summary["total_cost"] = total_cost
        wandb.run.summary["avg_cost_per_round"] = avg_cost_per_round
        wandb.run.summary["total_calls"] = total_calls
        wandb.run.summary["avg_calls_per_round"] = avg_calls_per_round
        wandb.run.summary["unattributed_cost"] = unattributed_cost
        wandb.run.summary["unattributed_calls"] = unattributed_calls
        wandb.run.summary["best_val_score"] = optimizer.best_score
        wandb.run.summary["total_rounds"] = optimizer.round
        wandb.finish()

    round_results = {
        "experiment_id": experiment_id,
        "config": experiment_config.model_dump(),
        "rounds": all_rounds,
        "summary": {
            "best_val_score": optimizer.best_score,
            "total_rounds": optimizer.round,
            "total_cost": total_cost,
            "avg_cost_per_round": avg_cost_per_round,
            "total_calls": total_calls,
            "avg_calls_per_round": avg_calls_per_round,
            **{f"{role}_total_input_tokens": totals[f"{role}_in"] for role in ("optimizer", "worker", "aggregator")},
            **{f"{role}_total_output_tokens": totals[f"{role}_out"] for role in ("optimizer", "worker", "aggregator")},
            **{f"{role}_total_cost": totals[f"{role}_cost"] for role in ("optimizer", "worker", "aggregator")},
            **{f"{role}_total_calls": totals[f"{role}_n_calls"] for role in ("optimizer", "worker", "aggregator")},
        },
    }
    with open(os.path.join(experiment_dir, "round_results.json"), "w") as f:
        json.dump(round_results, f, indent=2, default=str)

    with open(os.path.join(logs_dir, "optimizer_traces.json"), "w") as f:
        json.dump(optimizer.optimizer_traces, f, indent=2, default=str)

    by_round: dict = {}
    for r in call_tracker.records:
        round_key = r.get("round")
        bucket = by_round.setdefault(round_key, {
            "n_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "by_role": {},
            "by_phase": {},
        })
        bucket["n_calls"] += 1
        bucket["input_tokens"] += r.get("input_tokens") or 0
        bucket["output_tokens"] += r.get("output_tokens") or 0
        bucket["cost"] += r.get("cost") or 0.0
        role = r.get("role") or "unknown"
        phase = r.get("phase") or "unknown"
        bucket["by_role"][role] = bucket["by_role"].get(role, 0) + 1
        bucket["by_phase"][phase] = bucket["by_phase"].get(phase, 0) + 1
    round_calls_summary = {
        "experiment_id": experiment_id,
        "total_calls": len(call_tracker.records),
        "log_path": os.path.abspath(call_log_path),
        "rounds": {str(k): v for k, v in sorted(by_round.items(), key=lambda kv: (kv[0] is None, kv[0]))},
    }
    with open(os.path.join(logs_dir, "round_calls.json"), "w") as f:
        json.dump(round_calls_summary, f, indent=2, default=str)

    call_tracker.close()
