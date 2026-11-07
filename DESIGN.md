# Engineering design and invariants

1. **Eligibility precedes optimization.** A cheap but unauthorized model may never receive a high-risk task, even when all other providers are slow.
2. **Stable counterfactuals.** `uniform(seed, task_id, model, channel)` uses SHA-256 so all three policies see the same outcome for a given request/model pair without reliance on iteration order.
3. **Contextual learning.** UCB reward histories are keyed by `(task kind, model name)`. Unobserved eligible arms are selected first; a bounded uncertainty bonus balances exploration and exploitation.
4. **Transparent reward.** `reward = success - 0.2 × mock_cost_usd - 0.000025 × latency_ms`. Only the simulator's own definitions determine reward.
5. **Hindsight regret.** The highest reward of all permitted models for that task is computed *after the fact*. It is an optimistic comparator, not a deployable model-selection method.

A production model gateway also needs user privacy and data residency rules, dynamic service capabilities, provider failures, configurable route overrides, differential quality evaluation, budget allocation, and reliable metering. Those are outside this offline demonstration.

## Test boundaries

The unit suite checks catalog validation, token/difficulty limits, deterministic per-provider draws, high-risk enforcement across **all** routing strategies, upper confidence-bound executions, metrics, and escaped HTML. GitHub Actions runs the same suite on Python 3.11 and 3.12.
