#!/usr/bin/env python3
"""Static invariants for SuperGoal's shipped role cards and profiles.

Run: python3 hooks/test_config.py
"""
import tomllib
from pathlib import Path

from sync_model_profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
EXPECTED_ROLES = {
    "supergoal_luna_executor",
    "supergoal_researcher",
    "supergoal_reviewer",
}
PROFILE_ROLES = {
    "supergoal_luna_executor": "executor",
    "supergoal_researcher": "researcher",
    "supergoal_reviewer": "reviewer",
}
BUILTIN_NAMES = {"worker", "researcher", "reviewer", "explorer"}


def load_toml(path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


model_profile = load_profile(CONFIG / "model-profile.toml")
assert set(model_profile) == {"controller", "researcher", "executor", "reviewer"}
for role, settings in model_profile.items():
    assert isinstance(settings.get("model"), str) and settings["model"].strip(), role
    assert isinstance(settings.get("reasoning_effort"), str) and settings["reasoning_effort"].strip(), role

role_files = sorted(path for path in CONFIG.glob("supergoal_*.toml"))
assert {path.stem for path in role_files} == EXPECTED_ROLES

cards = {path.stem: load_toml(path) for path in role_files}
for stem, card in cards.items():
    assert card.get("name") == stem, "{} name/stem drift".format(stem)
    assert card["name"] not in BUILTIN_NAMES, "built-in role collision: {}".format(stem)
    assert card.get("description", "").strip(), "{} needs a description".format(stem)
    assert card.get("developer_instructions", "").strip(), "{} needs instructions".format(stem)
    profile_role = PROFILE_ROLES[stem]
    assert card.get("model") == model_profile[profile_role]["model"], stem
    assert card.get("model_reasoning_effort") == model_profile[profile_role]["reasoning_effort"], stem

executor = cards["supergoal_luna_executor"]
assert executor.get("sandbox_mode") == "workspace-write"
for required in ("one bounded workstream", "Do not globally re-plan", "spawn children", "validation evidence", "blockers"):
    assert required in executor["developer_instructions"], required

researcher = cards["supergoal_researcher"]
assert researcher.get("sandbox_mode") == "read-only"
for required in ("one assigned evidence question", "Do not edit files", "source URLs", "gaps"):
    assert required in researcher["developer_instructions"], required

reviewer = cards["supergoal_reviewer"]
assert reviewer.get("sandbox_mode") == "read-only"
for required in ("one supplied plan or merged result", "Do not edit files", "PASS", "FAIL", "CANNOT-VERIFY"):
    assert required in reviewer["developer_instructions"], required
assert "GO, REVISE" not in reviewer["developer_instructions"]

profile_path = CONFIG / "config.toml.snippet"
profile = load_toml(profile_path)
assert profile.get("model") == model_profile["controller"]["model"]
assert profile.get("model_reasoning_effort") == model_profile["controller"]["reasoning_effort"]
assert profile.get("features", {}).get("goals") is True
assert profile.get("agents") == {"max_threads": 10, "max_depth": 1}
assert "multi_agent_v2" not in profile.get("features", {})
assert "review_model" not in profile
assert "plan_mode_reasoning_effort" not in profile

profile_text = profile_path.read_text(encoding="utf-8")
for required in (
    "config/config.v2-strict.toml.snippet",
    "Do not merge its contents with",
):
    assert required in profile_text, required

strict_profile = load_toml(CONFIG / "config.v2-strict.toml.snippet")
assert strict_profile.get("model") == model_profile["controller"]["model"]
assert strict_profile.get("model_reasoning_effort") == model_profile["controller"]["reasoning_effort"]
assert strict_profile.get("features", {}).get("goals") is True
assert strict_profile.get("features", {}).get("multi_agent_v2") == {
    "enabled": True,
    "max_concurrent_threads_per_session": 11,
    "hide_spawn_agent_metadata": False,
}
assert "agents" not in strict_profile

manifest = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
for required in ("Plan-first", "independent workstreams", "named SuperGoal roles", "current evidence"):
    assert required in manifest, required
for stale in ("exact-10", "nine read-only research children"):
    assert stale not in manifest, stale

print("config self-check: all assertions passed")
