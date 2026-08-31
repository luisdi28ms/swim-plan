# Swim Plan

Turns a coach's swim workout plan into a structured Garmin Connect workout that syncs
to a watch, instead of manually typing sets into the Garmin Connect workout editor.

## Status

Phase 1 (done): push a hand-built swim workout to Garmin Connect and a device. Verified
end-to-end against a real account — a "Test Swim - 1000m" workout (200 warmup, 6x100 free
with lap-button rest, 200 cooldown, 25m pool) uploaded and pushed successfully to a
Forerunner 570.

Phase 2 (done): a `python -m swim_plan` CLI that builds a workout from a declarative JSON
spec file (see `examples/`) and uploads/pushes it — no new Python script per workout. The
translation from a coach's CSV/screenshot to a spec is done by a coding agent using the
glossary in `CLAUDE.md`.

## SDK research findings

- **`garminconnect`** (PyPI: `garminconnect`, GitHub: `cyberjunky/python-garminconnect`) is
  the library in use here. Actively maintained, no official Garmin API key or business
  partnership needed.
  - Auth uses Garmin's mobile SSO flow (same as the Android app), supports MFA, and caches
    an OAuth token to disk so you only do a full login once.
  - Ships a typed, Pydantic-based workout API (`garminconnect.workout`) with per-sport
    classes (`SwimmingWorkout`, `RunningWorkout`, `CyclingWorkout`, etc.) and step builder
    helpers, plus `Garmin.upload_swimming_workout()` / `Garmin.push_workout_to_device()`
    methods on the client.
- Garmin's official Connect Developer Program / Training API exists but is gated behind
  business/partner approval — not usable for a personal script. `garminconnect` talks to
  the same reverse-engineered endpoints the Garmin Connect web app and mobile app use.
- No existing "CSV → Garmin swim workout" tool was found; that's the gap this project
  fills.
- **Pool-swim specifics** (pool length, stroke type, distance-based sets, lap-button rest)
  are *not* documented in `garminconnect`'s README/examples — its own sample swim workout
  is time-based and has no pool length at all. The actual field names were reverse-engineered
  from `ThomasRondof/GarminWorkoutAItoJSON`'s JS source (which builds raw Garmin
  workout-service JSON) and confirmed against `garminconnect`'s own `workout.py` models,
  which allow extra fields (`model_config = ConfigDict(extra="allow")`) so this project can
  attach them without forking the library. See `swim_plan/swim_workout.py`.
  - `poolLength` / `poolLengthUnit` (`{"unitId": 1, "unitKey": "meter", "factor": 100}`) are
    set at both the workout level and the segment level.
  - `strokeType` is a dict per step: `{"strokeTypeId": ..., "strokeTypeKey": ..., "displayOrder": ...}`.
    `strokeTypeId` values: free=6, backstroke=2, breaststroke=3, fly=5, choice/none=0.
  - Rest steps end on lap-button press: `endCondition` `conditionTypeKey="lap.button"`
    (`conditionTypeId=1`), `endConditionValue=null` — this is what shows as "Lap Button
    Press" / "Duration" in the Garmin Connect UI (see the workout screenshot from the
    initial research).
  - Distance-based steps (warmup/interval/cooldown) use `conditionTypeKey="distance"`
    (`conditionTypeId=3`) with `endConditionValue` in meters and
    `preferredEndConditionUnit` set to the same meter unit dict.
- Fallback if the JSON workout API ever proves insufficient: Garmin's official FIT SDK
  supports a `workout` message with swim-specific step fields; a `.fit` file built that way
  can be manually imported into Garmin Connect. Not needed so far.

## Project layout

- `swim_plan/client.py` — `get_client()`: authenticated `Garmin` client from
  `GARMIN_EMAIL`/`GARMIN_PASSWORD` env vars, with token caching in `~/.garminconnect` (only
  needs a real login once; prompts for MFA on stdin if required).
- `swim_plan/swim_workout.py` — pool-swim workout builders: `warmup_step`, `swim_step`,
  `cooldown_step`, `rest_step` (lap-button), `timed_rest_step` (fixed seconds),
  `swim_repeat` ("N Times" block), and `build_swim_workout` to assemble a full
  `SwimmingWorkout`. Also `STROKE_TYPES` / `EQUIPMENT_TYPES` lookup dicts.
- `swim_plan/spec.py` — parses/validates a declarative JSON workout spec (steps, nested
  repeats, stroke, equipment, per-step notes, rest) and assembles the workout via the
  builders above. Step orders are assigned automatically; `_`-prefixed keys are comments.
- `swim_plan/cli.py` (+ `__main__.py`) — the `python -m swim_plan` CLI: `create` (build
  from a spec, upload, optionally `--push`; `--dry-run` prints the exact upload payload
  with no network calls), `list`, `delete`, `push`.
- `examples/test_1000m.json` — the sample 1000m workout above as a spec. Good smoke test
  (`create --dry-run`) after any change to `swim_workout.py`, `spec.py`, or `cli.py`.
- `examples/serie2_2026-08-24.json` — a real coach workout (Serie 2, semana de fondo)
  as a spec: nested repeats, fins/pull-buoy equipment, per-step Spanish notes, timed and
  lap-button rest.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in GARMIN_EMAIL / GARMIN_PASSWORD
.venv/bin/python -m swim_plan create examples/test_1000m.json --dry-run   # no credentials needed
.venv/bin/python -m swim_plan create examples/test_1000m.json --push      # upload + push to watch
```

(This machine's system Python had no `pip`; the venv had to be created with
`python3 -m venv --without-pip .venv` and pip bootstrapped via
`get-pip.py` — see git history if that's needed again elsewhere.)

## Next up

The workflow is now: a coding agent reads the coach's CSV/screenshot (glossary in
`CLAUDE.md`), writes a JSON spec per session, iterates with
`python -m swim_plan create <spec> --dry-run`, then runs `create --push`. No new Python
script per workout. Still open:

- Whether to auto-schedule the generated workout onto a calendar date
  (`Garmin.schedule_workout()` exists in the library) or just upload it to the library for
  manual scheduling.
- Pace/effort targets: "vel" (speed) and "suave" (easy) are still note text, not real
  Garmin intensity/pace targets (see CLAUDE.md "Known simplifications").
- A timed-rest-with-note combo, if a plan ever needs it (`rest` steps take no `note`).
