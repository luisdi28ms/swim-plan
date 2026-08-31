"""Build a ``SwimmingWorkout`` from a declarative JSON spec file.

The spec expresses the same primitives ``swim_workout.py`` exposes, so a new
workout is a data file instead of a new Python script.

Top-level shape::

    {
      "name": "Serie 2 - ...",          # required, workout name
      "description": "one-line label",  # optional, workout-level label ONLY
      "pool_length_meters": 25,         # optional, default 25
      "steps": [ ... ]                  # required, ordered list of steps
    }

Step shapes (keys that start with ``_`` are ignored everywhere — use them
for comments, e.g. ``"_comment": "8x15 vel VE"``)::

    {"type": "warmup"|"swim"|"cooldown",
     "distance": 100,                   # meters, required
     "stroke": "free",                  # optional, default "choice"
     "equipment": "fins",               # optional
     "note": "Velocidad, variando estilos"}   # optional per-step note
    {"type": "rest"}                    # lap-button rest
    {"type": "rest", "seconds": 10}     # timed rest
    {"type": "repeat", "times": 4, "steps": [ ... ]}   # nests freely

Step orders are assigned automatically (depth-first, starting at 1), so
specs never track them by hand. Rest steps take no ``note`` — that combo
is a known simplification (see CLAUDE.md).
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Iterator

from swim_plan.swim_workout import (
    EQUIPMENT_TYPES,
    STROKE_TYPES,
    build_swim_workout,
    cooldown_step,
    create_repeat_group,
    rest_step,
    swim_step,
    timed_rest_step,
    warmup_step,
)


class SpecError(ValueError):
    """The workout spec is invalid; the message says where and why."""


_DISTANCE_BUILDERS = {"warmup": warmup_step, "swim": swim_step, "cooldown": cooldown_step}
_STEP_TYPES = ("warmup", "swim", "cooldown", "rest", "repeat")


def load_spec(path: str | Path) -> dict[str, Any]:
    """Read and JSON-parse a spec file, with spec-level errors as SpecError."""
    spec_path = Path(path)
    try:
        raw = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"cannot read spec file {spec_path}: {exc}") from exc
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SpecError(f"{spec_path} is not valid JSON: {exc}") from exc
    if not isinstance(spec, dict):
        raise SpecError(f"{spec_path}: top level must be a JSON object")
    return spec


def _check_keys(obj: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = {key for key in obj if not key.startswith("_")} - allowed
    if unknown:
        raise SpecError(f"{where}: unknown key(s) {sorted(unknown)}; allowed keys: {sorted(allowed)}")


def _build_steps(items: Any, where: str, order: Iterator[int]) -> list[Any]:
    if not isinstance(items, list) or not items:
        raise SpecError(f"{where}: must be a non-empty list of steps")
    steps: list[Any] = []
    for index, item in enumerate(items, start=1):
        here = f"{where}[{index}]"
        if not isinstance(item, dict):
            raise SpecError(f"{here}: each step must be a JSON object")
        step_type = item.get("type")
        if step_type not in _STEP_TYPES:
            raise SpecError(f"{here}: 'type' must be one of {list(_STEP_TYPES)}, got {step_type!r}")

        if step_type == "repeat":
            _check_keys(item, {"type", "times", "steps"}, here)
            times = item.get("times")
            if not isinstance(times, int) or isinstance(times, bool) or times < 1:
                raise SpecError(f"{here}: 'times' must be an integer >= 1")
            group_order = next(order)
            children = _build_steps(item.get("steps"), f"{here}.steps", order)
            steps.append(create_repeat_group(times, children, group_order))
        elif step_type == "rest":
            _check_keys(item, {"type", "seconds"}, here)
            seconds = item.get("seconds")
            if seconds is None:
                steps.append(rest_step(next(order)))
            else:
                if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds <= 0:
                    raise SpecError(f"{here}: 'seconds' must be a number > 0 (omit it for lap-button rest)")
                steps.append(timed_rest_step(seconds, next(order)))
        else:
            _check_keys(item, {"type", "distance", "stroke", "equipment", "note"}, here)
            distance = item.get("distance")
            if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
                raise SpecError(f"{here}: 'distance' must be a number of meters > 0")
            stroke = item.get("stroke", "choice")
            if stroke not in STROKE_TYPES:
                raise SpecError(f"{here}: unknown stroke {stroke!r}; allowed: {sorted(STROKE_TYPES)}")
            equipment = item.get("equipment")
            if equipment is not None and equipment not in EQUIPMENT_TYPES:
                raise SpecError(f"{here}: unknown equipment {equipment!r}; allowed: {sorted(EQUIPMENT_TYPES)}")
            note = item.get("note")
            if note is not None and not isinstance(note, str):
                raise SpecError(f"{here}: 'note' must be a string")
            builder = _DISTANCE_BUILDERS[step_type]
            steps.append(builder(distance, next(order), stroke, equipment=equipment, note=note))
    return steps


def build_workout_from_spec(spec: dict[str, Any]):
    """Validate a parsed spec and assemble the SwimmingWorkout it describes."""
    _check_keys(spec, {"name", "description", "pool_length_meters", "steps"}, "spec")
    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SpecError("spec: 'name' must be a non-empty string")
    description = spec.get("description")
    if description is not None and not isinstance(description, str):
        raise SpecError("spec: 'description' must be a string (one-line workout label)")
    pool_length = spec.get("pool_length_meters", 25)
    if not isinstance(pool_length, (int, float)) or isinstance(pool_length, bool) or pool_length <= 0:
        raise SpecError("spec: 'pool_length_meters' must be a number > 0")

    steps = _build_steps(spec.get("steps"), "steps", itertools.count(1))
    return build_swim_workout(
        name=name,
        steps=steps,
        pool_length_meters=pool_length,
        description=description,
    )


def total_distance_meters(payload: dict[str, Any]) -> float:
    """Total swim distance of a built workout payload (repeat-aware), for sanity checks."""

    def walk(step_dicts: list[dict[str, Any]]) -> float:
        total = 0.0
        for step in step_dicts:
            if step.get("stepType", {}).get("stepTypeKey") == "repeat":
                total += step.get("numberOfIterations", 1) * walk(step.get("workoutSteps", []))
            elif step.get("endCondition", {}).get("conditionTypeKey") == "distance":
                total += step.get("endConditionValue") or 0.0
        return total

    return walk(payload["workoutSegments"][0]["workoutSteps"])
