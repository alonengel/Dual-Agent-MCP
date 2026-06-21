"""Tests for JSON report builders and persistence."""

from __future__ import annotations

import json

from copthief.reporting.report import (
    build_bonus_report,
    build_internal_report,
    save_report,
)

_MATCH = {"sub_games": [{"index": 1, "outcome": "cop_win"}], "totals": {"cop": 20, "thief": 5}}


def test_build_internal_report_shape() -> None:
    team = {"group_name": "T", "students": ["a"], "github_repo": "u", "timezone": "Asia/Jerusalem"}
    mcp = {"cop_url": "c", "thief_url": "t"}
    report = build_internal_report(team, mcp, _MATCH)
    assert report["group_name"] == "T"
    assert report["cop_mcp_url"] == "c"
    assert report["totals"]["cop"] == 20


def test_build_bonus_report_shape() -> None:
    g1 = {"group_name": "A", "github_repo": "ga", "cop_url": "ac", "thief_url": "at"}
    g2 = {"group_name": "B", "github_repo": "gb", "cop_url": "bc", "thief_url": "bt"}
    match = {"sub_games": [], "totals_by_group": {"A": 60, "B": 80}}
    report = build_bonus_report(g1, g2, match, agreement=True)
    assert report["report_type"] == "bonus_game"
    assert report["groups"]["group_2"] == "B"
    assert report["mutual_agreement"] is True


def test_save_report_writes_json(tmp_path) -> None:
    path = save_report({"a": 1}, tmp_path, prefix="x")
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
