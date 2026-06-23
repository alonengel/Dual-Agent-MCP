"""Tests for the LLM usage meter and the gatekeeper-wired provider path."""

from __future__ import annotations

from copthief.llm.mock import MockProvider
from copthief.shared.gatekeeper import ApiGatekeeper
from copthief.shared.usage import UsageMeter, estimate_tokens


def test_estimate_tokens_has_floor_and_scales() -> None:
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 8) == 2


def test_meter_records_tokens_and_estimates_cost() -> None:
    meter = UsageMeter(pricing={"m": (1000.0, 2000.0), "default": (0.0, 0.0)})
    meter.record("m", "x" * 40, "y" * 80)  # 10 input, 20 output tokens
    summary = meter.summary()
    assert summary["by_model"]["m"]["input_tokens"] == 10
    assert summary["by_model"]["m"]["output_tokens"] == 20
    assert summary["by_model"]["m"]["est_usd"] == 0.05
    assert summary["totals"] == {"calls": 1, "input_tokens": 10,
                                 "output_tokens": 20, "est_usd": 0.05}


def test_meter_unknown_model_is_free() -> None:
    meter = UsageMeter()
    meter.record("unknown", "abcd", "efgh")
    assert meter.summary()["totals"]["est_usd"] == 0.0


def test_provider_routes_through_gatekeeper_and_meter() -> None:
    meter = UsageMeter()
    gate = ApiGatekeeper({"requests_per_minute": 600, "max_retries": 1})
    provider = MockProvider("mock").attach(gate, meter)
    out = provider.complete("sys", "ROLE: cop\nDIRECTIVE: go north")
    assert "cop" in out
    assert meter.summary()["totals"]["calls"] == 1
