"""Per-call tracking for AsyncLLM during AFlow searches.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import threading
import time
import uuid
from typing import Optional

# --- Context variables ----------------------------------------------------
ctx_round: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "ctx_round", default=None
)
ctx_phase: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "ctx_phase", default=None
)
ctx_validation_repeat: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "ctx_validation_repeat", default=None
)
ctx_puzzle_idx: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "ctx_puzzle_idx", default=None
)
ctx_call_budget: contextvars.ContextVar[Optional["CallBudget"]] = contextvars.ContextVar(
    "ctx_call_budget", default=None
)


class CallBudgetExceeded(Exception):
    """Raised by the tracked AsyncLLM wrapper when a workflow exceeds its
    per-execution call limit. Caught by `evaluate_problem` (which already
    handles arbitrary Exception → score=0), so a runaway workflow records a
    failed puzzle instead of burning unbounded tokens."""

    def __init__(self, limit: int, count: int):
        super().__init__(
            f"Workflow call budget exceeded: {count} calls > limit {limit}"
        )
        self.limit = limit
        self.count = count


class CallBudget:
    """Counts LLM calls for a single workflow execution and rejects new ones
    once the limit is exceeded.

    The 'tripped' flag matters because `enigmata.py:_generate_output` is
    wrapped in `@retry(stop_after_attempt=5)`. Without the flag, every
    retry would re-enter the workflow, see the count was at the limit,
    raise, decrement-retry... still raising at the wrapper, but the calls
    that already happened in earlier attempts are double-counted from the
    user's perspective. With the flag, every call after the trip is a
    fast pre-network raise — bounded blast radius.
    """

    __slots__ = ("limit", "count", "tripped")

    def __init__(self, limit: Optional[int]):
        self.limit = limit
        self.count = 0
        self.tripped = False

    def consume(self) -> None:
        if self.tripped:
            raise CallBudgetExceeded(self.limit or -1, self.count)
        self.count += 1
        if self.limit is not None and self.count > self.limit:
            self.tripped = True
            raise CallBudgetExceeded(self.limit, self.count)


def set_call_budget(budget: Optional["CallBudget"]):
    return _CtxToken(ctx_call_budget, ctx_call_budget.set(budget))


# Module-level default limit applied to every puzzle's workflow. None
# disables the budget. search.py sets this from the CLI before the search
# starts; benchmark.evaluate_all_problems reads it when minting per-puzzle
# CallBudgets.
_default_workflow_call_limit: Optional[int] = None


def set_workflow_call_limit(limit: Optional[int]) -> None:
    global _default_workflow_call_limit
    _default_workflow_call_limit = limit


def get_workflow_call_limit() -> Optional[int]:
    return _default_workflow_call_limit


class _NullCtx:
    """Sync no-op context manager for the `with set_*` pattern below."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _CtxToken:
    """Restore a contextvar on `__exit__`. Used by the set_* helpers below."""

    def __init__(self, var, token):
        self._var = var
        self._token = token

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._var.reset(self._token)
        return False


def set_round(round_idx: Optional[int]):
    return _CtxToken(ctx_round, ctx_round.set(round_idx))


def set_phase(phase: Optional[str]):
    return _CtxToken(ctx_phase, ctx_phase.set(phase))


def set_validation_repeat(idx: Optional[int]):
    return _CtxToken(ctx_validation_repeat, ctx_validation_repeat.set(idx))


def set_puzzle_idx(idx: Optional[int]):
    return _CtxToken(ctx_puzzle_idx, ctx_puzzle_idx.set(idx))


# --- Tracker ---------------------------------------------------------------


class CallTracker:
    """Captures every AsyncLLM call to a JSONL file + an in-memory list.

    The in-memory copy is what `search.py` summarizes at the end of the run
    (per-round call counts, total tokens). The JSONL is the per-call ground
    truth — full prompts and responses included, one record per line.
    """

    def __init__(self, log_path: str):
        self.log_path = log_path
        self._fh = open(log_path, "w", buffering=1)  # line-buffered
        self._lock = threading.Lock()  # protects file writes + records list
        self.records: list[dict] = []
        self._installed = False
        self._original_call = None

    def write(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            self._fh.write(line + "\n")
            self.records.append(record)

    @property
    def records_by_round(self) -> dict:
        out: dict = {}
        for r in self.records:
            out.setdefault(r.get("round"), []).append(r)
        return out

    def close(self) -> None:
        with self._lock:
            if not self._fh.closed:
                self._fh.close()
        if self._installed and self._original_call is not None:
            from scripts.async_llm import AsyncLLM
            AsyncLLM.__call__ = self._original_call
            self._installed = False


_active_tracker: Optional[CallTracker] = None


def install_call_tracking(log_path: str) -> CallTracker:
    """Patch `AsyncLLM.__call__` to log every call into `log_path`.

    Idempotent within a process: a second install replaces the active tracker
    (the original `__call__` is restored from the first install before the
    second patch is applied, so we don't accumulate wrappers).
    """
    global _active_tracker
    from scripts.async_llm import AsyncLLM, ctx_usage_scope

    if _active_tracker is not None:
        _active_tracker.close()

    tracker = CallTracker(log_path)
    tracker._original_call = AsyncLLM.__call__
    tracker._installed = True

    original_call = tracker._original_call

    async def tracked_call(self, prompt):
        call_id = uuid.uuid4().hex
        t_start = time.time()
        # Capture context *before* the call: contextvars set by the optimizer
        # / evaluation utilities reflect what was active at the moment we
        # entered the LLM call.
        round_idx = ctx_round.get()
        phase = ctx_phase.get()
        val_repeat = ctx_validation_repeat.get()
        puzzle_idx = ctx_puzzle_idx.get()
        role = getattr(getattr(self, "config", None), "_role", None)

        # Per-call delta strategy:
        #
        # The original AsyncLLM.usage_tracker is a single mutable counter
        # shared across every concurrent puzzle that holds a reference to
        # this AsyncLLM instance. Snapshotting `total_cost` and the
        # usage_history length at call entry races with sibling tasks: two
        # parallel calls both record `before_cost=X`, the first finishes
        # (X+a), the second finishes (X+a+b), and the second reports a+b.
        #
        # ctx_usage_scope (defined in async_llm.py and bumped inside
        # AsyncLLM.__call__) holds a *task-local* dict of per-instance
        # buckets. Each puzzle's evaluate_problem task starts with a fresh
        # empty scope (set by benchmark.evaluate_all_problems), so reading
        # `scope[id(self)]` before/after the call gives us the delta for
        # exactly *this* call within *this* task — race-free.
        #
        # Outside a scope (the optimizer-LLM path: one sequential call per
        # round, no concurrent siblings on the same instance) we fall back
        # to reading the most recently appended usage_history record, which
        # is correct precisely because no other call is in flight.
        scope = ctx_usage_scope.get()
        if scope is not None:
            bucket = scope.get(id(self))
            in_before = bucket["total_input_tokens"] if bucket else 0
            out_before = bucket["total_output_tokens"] if bucket else 0
            cost_before = bucket["total_cost"] if bucket else 0.0
            before_len = None  # unused on the scoped path
        else:
            in_before = out_before = 0
            cost_before = 0.0
            before_len = len(self.usage_tracker.usage_history)
        error: Optional[str] = None
        response = None
        budget = ctx_call_budget.get()
        try:
            # Pre-network: check the per-workflow call budget. Raises
            # CallBudgetExceeded — which evaluate_problem catches and turns
            # into a score=0 outcome for the killed puzzle.
            if budget is not None:
                budget.consume()
            response = await original_call(self, prompt)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            t_end = time.time()
            input_tokens = None
            output_tokens = None
            cost = None
            try:
                if scope is not None:
                    bucket_after = scope.get(id(self))
                    if bucket_after is not None:
                        input_tokens = bucket_after["total_input_tokens"] - in_before
                        output_tokens = bucket_after["total_output_tokens"] - out_before
                        cost = bucket_after["total_cost"] - cost_before
                elif before_len is not None and len(self.usage_tracker.usage_history) > before_len:
                    # Sequential path (optimizer LLM): the record we just
                    # added sits at index `before_len`.
                    usage_record = self.usage_tracker.usage_history[before_len]
                    input_tokens = usage_record.get("input_tokens")
                    output_tokens = usage_record.get("output_tokens")
                    cost = usage_record.get("total_cost")
            except Exception:
                pass

            record = {
                "call_id": call_id,
                "t_start": t_start,
                "t_end": t_end,
                "latency_sec": t_end - t_start,
                "round": round_idx,
                "phase": phase,
                "validation_repeat": val_repeat,
                "puzzle_idx": puzzle_idx,
                "workflow_call_idx": budget.count if budget is not None else None,
                "workflow_call_limit": budget.limit if budget is not None else None,
                "role": role,
                "model": getattr(getattr(self, "config", None), "model", None),
                "temperature": getattr(getattr(self, "config", None), "temperature", None),
                "prompt": prompt,
                "response": response,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "error": error,
            }
            if _active_tracker is not None:
                _active_tracker.write(record)

        return response

    AsyncLLM.__call__ = tracked_call
    _active_tracker = tracker
    return tracker


def get_active_tracker() -> Optional[CallTracker]:
    return _active_tracker
