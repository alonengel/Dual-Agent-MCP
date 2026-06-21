"""Builds the structured JSON reports required by the assignment (sections 9.1/9.2)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_internal_report(team: dict[str, Any], mcp: dict[str, Any],
                          match: dict[str, Any]) -> dict[str, Any]:
    """Assemble the internal (self-play) game report JSON."""
    return {
        "group_name": team.get("group_name", ""),
        "students": team.get("students", []),
        "github_repo": team.get("github_repo", ""),
        "cop_mcp_url": mcp.get("cop_url", ""),
        "thief_mcp_url": mcp.get("thief_url", ""),
        "timezone": team.get("timezone", "Asia/Jerusalem"),
        "sub_games": match.get("sub_games", []),
        "totals": match.get("totals", {}),
    }


def build_bonus_report(group_1: dict[str, Any], group_2: dict[str, Any],
                       match: dict[str, Any], agreement: bool = True) -> dict[str, Any]:
    """Assemble the inter-group bonus report JSON (two teams, mutual agreement)."""
    totals = match.get("totals_by_group", {})
    return {
        "report_type": "bonus_game",
        "groups": {"group_1": group_1.get("group_name"), "group_2": group_2.get("group_name")},
        "github_repo_group_1": group_1.get("github_repo", ""),
        "github_repo_group_2": group_2.get("github_repo", ""),
        "mcp_url_group_1_cop": group_1.get("cop_url", ""),
        "mcp_url_group_1_thief": group_1.get("thief_url", ""),
        "mcp_url_group_2_cop": group_2.get("cop_url", ""),
        "mcp_url_group_2_thief": group_2.get("thief_url", ""),
        "timezone": "Asia/Jerusalem",
        "sub_games": match.get("sub_games", []),
        "totals_by_group": totals,
        "mutual_agreement": agreement,
    }


def save_report(report: dict[str, Any], results_dir: Path, prefix: str = "report") -> Path:
    """Persist a report to a timestamped JSON file and return its path."""
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = results_dir / f"{prefix}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
