"""Token-usage accounting and cost estimation for LLM calls.

The meter is updated by the LLM base class after every completion so the project
can report per-model token counts and an estimated USD cost (PDF/guidelines §11).
Local CLI/mock providers price at zero; cloud models use a configurable table.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Rough chars-per-token ratio; accurate enough for cost estimation across vendors.
_CHARS_PER_TOKEN = 4
# Default USD price per 1M tokens as (input, output). Overridable via config.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "gpt-4o": (2.5, 10.0),
    "default": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length (min 1 so empty strings still count)."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


@dataclass
class _ModelUsage:
    """Running token totals for a single model."""

    calls: int = 0
    in_tokens: int = 0
    out_tokens: int = 0


@dataclass
class UsageMeter:
    """Accumulate per-model token usage and estimate cost from a price table."""

    pricing: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(_PRICING))
    by_model: dict[str, _ModelUsage] = field(default_factory=dict)

    def record(self, model: str, prompt: str, completion: str) -> None:
        """Add one completion's input/output token estimate to the model's totals."""
        usage = self.by_model.setdefault(model, _ModelUsage())
        usage.calls += 1
        usage.in_tokens += estimate_tokens(prompt)
        usage.out_tokens += estimate_tokens(completion)

    def _cost_usd(self, model: str, usage: _ModelUsage) -> float:
        """Estimate USD for a model from its tokens and the price table."""
        rate_in, rate_out = self.pricing.get(model, self.pricing["default"])
        return (usage.in_tokens * rate_in + usage.out_tokens * rate_out) / 1_000_000

    def summary(self) -> dict:
        """Return per-model token/cost breakdown plus aggregate totals."""
        by_model: dict[str, dict] = {}
        total_in = total_out = 0
        total_usd = 0.0
        for model, usage in self.by_model.items():
            cost = self._cost_usd(model, usage)
            by_model[model] = {"calls": usage.calls, "input_tokens": usage.in_tokens,
                               "output_tokens": usage.out_tokens, "est_usd": round(cost, 4)}
            total_in += usage.in_tokens
            total_out += usage.out_tokens
            total_usd += cost
        totals = {"calls": sum(m["calls"] for m in by_model.values()),
                  "input_tokens": total_in, "output_tokens": total_out,
                  "est_usd": round(total_usd, 4)}
        return {"by_model": by_model, "totals": totals}
