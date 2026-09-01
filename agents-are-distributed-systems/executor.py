"""The agent step executor that the frameworks do not give you.

Everything here was standard practice for service-to-service calls before
anyone said the word agent. We handed the caller role to a non-deterministic
component and shipped none of it.

  idempotency keys      because a timeout is an unknown outcome, not a failure
  effect classification because retrying a read is free and retrying a booking
                        is not, and the framework cannot tell them apart
  replan over retry     because a failure caused by context reproduces itself
                        when you retry with the same context
  budgets               steps AND spend, because a step's cost varies by orders
                        of magnitude with accumulated context
  a trace               because a ten step task that failed at step seven is
                        undebuggable without one
"""
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Effect(Enum):
    """Whether repeating this call is safe.

    The single most important field in this file, and no agent framework asks
    you for it. Without it, the executor cannot know that retrying a search is
    free and retrying a booking double-books someone.
    """
    READ = "read"              # safe to repeat freely
    IDEMPOTENT = "idempotent"  # safe to repeat WITH a key
    MUTATING = "mutating"      # never repeat without confirming outcome


class Outcome(Enum):
    OK = "ok"
    TRANSIENT = "transient"    # retry the same call
    PERSISTENT = "persistent"  # rebuild context, do not retry blindly
    UNKNOWN = "unknown"        # timeout. May have committed.


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class Tool:
    name: str
    effect: Effect
    fn: Callable[[dict], Any]
    timeout_s: float = 10.0


@dataclass
class TraceEvent:
    step: int
    tool: str
    outcome: str
    attempt: int
    idempotency_key: str | None
    elapsed_ms: float
    note: str = ""


@dataclass
class StepBudget:
    """Steps and spend, because they are not the same constraint.

    A single step's cost varies by orders of magnitude depending on how much
    context it accumulated, so a step cap alone does not bound spend.
    """
    max_steps: int = 12
    max_spend: float = 1.00
    steps_used: int = 0
    spend_used: float = 0.0

    def charge(self, steps: int = 1, cost: float = 0.0) -> None:
        self.steps_used += steps
        self.spend_used += cost
        if self.steps_used > self.max_steps:
            raise BudgetExhausted(f"step budget {self.max_steps} exhausted")
        if self.spend_used > self.max_spend:
            raise BudgetExhausted(f"spend budget {self.max_spend} exhausted")


def idempotency_key(task_id: str, step: int, tool: str, args: dict) -> str:
    """Stable across retries of the SAME logical operation, different across
    genuinely different operations. Includes the arguments, so a replan that
    changes them correctly produces a new key."""
    payload = json.dumps({"task": task_id, "step": step, "tool": tool,
                          "args": args}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


@dataclass
class Executor:
    tools: dict[str, Tool]
    budget: StepBudget = field(default_factory=StepBudget)
    trace: list[TraceEvent] = field(default_factory=list)
    max_retries: int = 2
    _seen_keys: set = field(default_factory=set)

    def run_step(self, task_id: str, step: int, tool_name: str, args: dict,
                 replan: Callable[[str], dict] | None = None):
        tool = self.tools[tool_name]
        current_args = args

        for attempt in range(self.max_retries + 1):
            self.budget.charge(cost=0.02)
            key = (idempotency_key(task_id, step, tool_name, current_args)
                   if tool.effect is not Effect.READ else None)

            started = time.perf_counter()
            outcome, value, note = self._invoke(tool, current_args, key)
            self.trace.append(TraceEvent(
                step, tool_name, outcome.value, attempt, key,
                (time.perf_counter() - started) * 1000, note))

            if outcome is Outcome.OK:
                return value

            if outcome is Outcome.UNKNOWN:
                # A timeout is not a failure. Never blindly repeat a mutation.
                if tool.effect is Effect.MUTATING:
                    raise RuntimeError(
                        f"{tool_name} timed out and is MUTATING. Outcome is "
                        f"unknown; confirm before any retry. Key: {key}")
                continue        # keyed replay is safe for READ and IDEMPOTENT

            if outcome is Outcome.PERSISTENT:
                if replan is None:
                    raise RuntimeError(
                        f"{tool_name} failed persistently and no replan was "
                        f"supplied. Retrying the same context reproduces it.")
                current_args = replan(note)     # new context, new key

        raise RuntimeError(f"{tool_name} exhausted {self.max_retries} retries")

    def _invoke(self, tool: Tool, args: dict, key: str | None):
        if key is not None and key in self._seen_keys:
            return Outcome.OK, {"deduplicated": True}, "replayed, no new effect"
        try:
            value = tool.fn(args)
        except TimeoutError as e:
            return Outcome.UNKNOWN, None, str(e)
        except ValueError as e:
            return Outcome.PERSISTENT, None, str(e)     # bad args, context fault
        except ConnectionError as e:
            return Outcome.TRANSIENT, None, str(e)
        if key is not None:
            self._seen_keys.add(key)
        return Outcome.OK, value, ""
