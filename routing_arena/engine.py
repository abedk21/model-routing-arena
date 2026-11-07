"""Deterministic contextual routing simulator; no model or cloud calls."""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

KINDS = ("chat", "code", "analysis")
POLICIES = ("cheapest", "quality_first", "adaptive_ucb")


class ConfigError(ValueError):
    """Invalid workload or model catalog."""


def uniform(seed: int, task_id: str, model: str, channel: str) -> float:
    """Stable pseudo-random draw shared across policy comparisons."""
    digest = hashlib.sha256(f"v1|{seed}|{task_id}|{model}|{channel}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def validate_config(models: list[dict], tasks: list[dict]) -> None:
    if not models or not tasks:
        raise ConfigError("Nonempty model catalog and workload required")
    names = set()
    for model in models:
        name = model.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ConfigError("Models need unique, nonempty names")
        names.add(name)
        if set(model.get("kinds", [])) - set(KINDS) or not model.get("kinds"):
            raise ConfigError("Every model must support at least one known task kind")
        for field in ("cost_input_per_m", "cost_output_per_m", "base_latency_ms", "ms_per_output_token"):
            v = model.get(field)
            if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                raise ConfigError(f"Invalid {field} for {name}")
        quality = model.get("quality")
        if not isinstance(quality, dict) or set(quality) != set(model["kinds"]):
            raise ConfigError(f"Quality scores must cover supported kinds for {name}")
        if any(type(v) not in (int, float) or not 0 <= v <= 1 for v in quality.values()):
            raise ConfigError("Quality must be a probability")
        if not isinstance(model.get("high_risk_approved"), bool):
            raise ConfigError("high_risk_approved must be boolean")
    ids = set()
    for task in tasks:
        tid = task.get("id")
        if not isinstance(tid, str) or not tid or tid in ids:
            raise ConfigError("Tasks need unique, nonempty IDs")
        ids.add(tid)
        if task.get("kind") not in KINDS or task.get("risk") not in ("low", "high"):
            raise ConfigError("Unrecognized task kind or risk")
        if type(task.get("difficulty")) not in (float, int) or not 0 <= task["difficulty"] <= 1:
            raise ConfigError("Difficulty must be between 0 and 1")
        for key in ("input_tokens", "output_tokens"):
            if type(task.get(key)) is not int or not 0 < task[key] <= 100000:
                raise ConfigError("Tokens must be positive bounded integers")
        if not eligible(models, task):
            raise ConfigError(f"No policy-approved model for task {tid}")


def eligible(models: list[dict], task: dict) -> list[dict]:
    return [m for m in models if task["kind"] in m["kinds"] and
            (task["risk"] != "high" or m["high_risk_approved"])]


def estimated_quality(model: dict, task: dict) -> float:
    return max(0.02, min(0.99, model["quality"][task["kind"]] - .27 * task["difficulty"]))


def estimate_cost(model: dict, task: dict) -> float:
    return (model["cost_input_per_m"] * task["input_tokens"] +
            model["cost_output_per_m"] * task["output_tokens"]) / 1_000_000


@dataclass(frozen=True)
class Outcome:
    task_id: str
    kind: str
    risk: str
    model: str
    success: bool
    success_probability: float
    latency_ms: int
    cost_usd: float
    reward: float


def run_model(model: dict, task: dict, seed: int) -> Outcome:
    if model not in eligible([model], task):
        raise ConfigError("Disallowed model for task")
    probability = estimated_quality(model, task)
    success = uniform(seed, task["id"], model["name"], "quality") < probability
    jitter = 0.82 + 0.36 * uniform(seed, task["id"], model["name"], "latency")
    latency = round((model["base_latency_ms"] +
                     model["ms_per_output_token"] * task["output_tokens"]) * jitter)
    cost = estimate_cost(model, task)
    reward = (1.0 if success else 0.0) - 0.20 * cost - 0.000025 * latency
    return Outcome(task["id"], task["kind"], task["risk"], model["name"],
                   success, round(probability, 4), latency, round(cost, 8), round(reward, 6))


def _p95(nums: list[int]) -> int:
    return sorted(nums)[math.ceil(0.95 * len(nums)) - 1]


def simulate(models: list[dict], tasks: list[dict], policy: str, seed: int = 41) -> dict[str, Any]:
    validate_config(models, tasks)
    if policy not in POLICIES or type(seed) is not int:
        raise ConfigError("Unsupported policy or seed")
    stats: dict[tuple[str, str], list[float]] = defaultdict(list)
    records: list[Outcome] = []
    regrets = []
    for task in tasks:
        choices = eligible(models, task)
        if policy == "cheapest":
            selected = min(choices, key=lambda m: (estimate_cost(m, task), m["name"]))
        elif policy == "quality_first":
            selected = min(choices, key=lambda m: (-estimated_quality(m, task), m["name"]))
        else:
            # Explore each supported arm for each context, then choose a UCB score.
            untested = [m for m in choices if not stats[(task["kind"], m["name"])]]
            if untested:
                selected = min(untested, key=lambda m: m["name"])
            else:
                total = sum(len(stats[(task["kind"], m["name"])]) for m in choices)
                def ucb(m: dict) -> tuple[float, str]:
                    history = stats[(task["kind"], m["name"])]; n = len(history)
                    score = sum(history) / n + 0.32 * math.sqrt(2 * math.log(total + 1) / n)
                    return (-score, m["name"])
                selected = min(choices, key=ucb)
        outcome = run_model(selected, task, seed)
        records.append(outcome)
        stats[(task["kind"], selected["name"])].append(outcome.reward)
        hindsight = max(run_model(m, task, seed).reward for m in choices)
        regrets.append(max(0.0, hindsight - outcome.reward))
    successes = sum(o.success for o in records)
    costs = sum(o.cost_usd for o in records)
    counts = {m["name"]: sum(o.model == m["name"] for o in records) for m in models}
    return {"policy": policy, "seed": seed, "count": len(records),
            "success_rate": round(successes / len(records), 4),
            "total_cost_usd": round(costs, 6),
            "p95_latency_ms": _p95([o.latency_ms for o in records]),
            "average_reward": round(sum(o.reward for o in records) / len(records), 5),
            "hindsight_regret": round(sum(regrets), 5),
            "model_counts": counts,
            "outcomes": [asdict(o) for o in records]}


def compare_policies(models: list[dict], tasks: list[dict], seed: int = 41) -> list[dict]:
    return [simulate(models, tasks, policy, seed) for policy in POLICIES]
