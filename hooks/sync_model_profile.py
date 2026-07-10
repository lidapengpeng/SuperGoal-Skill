#!/usr/bin/env python3
"""Synchronize shipped Codex cards and controller snippets from one profile.

Run `python3 hooks/sync_model_profile.py --check --catalog-check` after
editing `config/model-profile.toml`; add `--write` to update generated assets.
"""

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path


ROLES = ("controller", "researcher", "executor", "reviewer")
EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
PROFILE_KEYS = {"model", "reasoning_effort"}
ASSETS = (
    ("config/config.toml.snippet", "controller"),
    ("config/config.v2-strict.toml.snippet", "controller"),
    ("config/supergoal_researcher.toml", "researcher"),
    ("config/supergoal_luna_executor.toml", "executor"),
    ("config/supergoal_reviewer.toml", "reviewer"),
)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def load_profile(path):
    try:
        with Path(path).open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError("could not read model profile: {}".format(error)) from error

    unknown_roles = sorted(set(raw) - set(ROLES))
    if unknown_roles:
        listed = ", ".join("[{}]".format(role) for role in unknown_roles)
        if "discussor" in unknown_roles:
            raise ValueError(
                "profile has unsupported section(s) {}; SuperGoal has no [discussor] role; use [reviewer]".format(listed)
            )
        raise ValueError("profile has unsupported section(s): {}".format(listed))

    profile = {}
    for role in ROLES:
        entry = raw.get(role)
        if not isinstance(entry, dict):
            raise ValueError("profile is missing [{}]".format(role))
        unknown_keys = sorted(set(entry) - PROFILE_KEYS)
        if unknown_keys:
            raise ValueError(
                "[{}] has unsupported key(s): {}".format(role, ", ".join(unknown_keys))
            )
        model = entry.get("model")
        effort = entry.get("reasoning_effort")
        if not _text(model):
            raise ValueError("[{}].model must be a non-empty string".format(role))
        if effort not in EFFORTS:
            raise ValueError(
                "[{}].reasoning_effort must be one of {}".format(
                    role, ", ".join(sorted(EFFORTS))
                )
            )
        profile[role] = {"model": model, "reasoning_effort": effort}
    return profile


def load_local_model_catalog():
    """Return `{model: {reasoning_effort, ...}}` from the active Codex CLI."""
    try:
        completed = subprocess.run(
            ["codex", "debug", "models"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ValueError("could not start `codex debug models`: {}".format(error)) from error
    if completed.returncode:
        raise ValueError("`codex debug models` exited with {}".format(completed.returncode))
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("`codex debug models` did not return JSON") from error

    catalog = {}
    for item in raw.get("models", []):
        slug = item.get("slug") if isinstance(item, dict) else None
        levels = item.get("supported_reasoning_levels") if isinstance(item, dict) else None
        if _text(slug) and isinstance(levels, list):
            catalog[slug] = {
                level.get("effort")
                for level in levels
                if isinstance(level, dict) and _text(level.get("effort"))
            }
    if not catalog:
        raise ValueError("`codex debug models` returned no usable model catalog")
    return catalog


def validate_local_model_catalog(profile, catalog):
    """Return profile entries unavailable in an explicit local model catalog."""
    problems = []
    for role in ROLES:
        model = profile[role]["model"]
        effort = profile[role]["reasoning_effort"]
        supported_efforts = catalog.get(model)
        if supported_efforts is None:
            problems.append("[{}].model {!r} is unavailable in the local Codex catalog".format(role, model))
        elif effort not in supported_efforts:
            problems.append(
                "[{}].reasoning_effort {!r} is not supported by {}; choose {}".format(
                    role, effort, model, ", ".join(sorted(supported_efforts))
                )
            )
    return problems


def _replace_assignment(text, key, value, path):
    pattern = re.compile(r"(?m)^(" + re.escape(key) + r"\s*=\s*)\"[^\"\n]*\"(\s*)$")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError("{} must contain exactly one {} assignment".format(path, key))
    return pattern.sub(r"\1" + json.dumps(value) + r"\2", text, count=1)


def planned_updates(root, profile):
    root = Path(root)
    updates = {}
    for relative, role in ASSETS:
        path = root / relative
        try:
            original = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError("could not read {}: {}".format(path, error)) from error
        updated = _replace_assignment(original, "model", profile[role]["model"], path)
        updated = _replace_assignment(
            updated, "model_reasoning_effort", profile[role]["reasoning_effort"], path
        )
        if updated != original:
            updates[path] = updated
    return updates


def write_updates(updates):
    for path, text in updates.items():
        path.write_text(text, encoding="utf-8")


def main(argv=None):
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default, help="plugin root")
    parser.add_argument("--profile", type=Path, help="profile TOML (defaults under --root)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="apply profile values to shipped assets")
    mode.add_argument("--check", action="store_true", help="report shipped-asset drift without writing (default)")
    parser.add_argument(
        "--catalog-check",
        action="store_true",
        help="verify each selected model/effort against `codex debug models`",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    profile_path = args.profile or root / "config" / "model-profile.toml"
    try:
        profile = load_profile(profile_path)
        if args.catalog_check:
            catalog_problems = validate_local_model_catalog(profile, load_local_model_catalog())
            if catalog_problems:
                for problem in catalog_problems:
                    print("sync_model_profile: {}".format(problem), file=sys.stderr)
                return 2
            print("local Codex model catalog supports profile")
        updates = planned_updates(root, profile)
    except ValueError as error:
        print("sync_model_profile: {}".format(error), file=sys.stderr)
        return 2

    if args.write:
        write_updates(updates)
        for path in updates:
            print("updated {}".format(path.relative_to(root)))
        if not updates:
            print("shipped model-profile assets are already in sync")
        return 0

    if updates:
        for path in updates:
            print("out of sync: {}".format(path.relative_to(root)))
        return 1
    print("shipped model-profile assets are in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
