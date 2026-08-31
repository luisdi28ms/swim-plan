# Swim Plan

Turns a coach's swim workout plan into a structured Garmin Connect workout that syncs
to a watch, instead of manually typing sets into the Garmin Connect workout editor.

## Status

Phase 1 (done): push a hand-built swim workout to Garmin Connect and a device. Verified
end-to-end against a real account — a "Test Swim - 1000m" workout (200 warmup, 6x100 free
with lap-button rest, 200 cooldown, 25m pool) uploaded and pushed successfully to a
Forerunner 570.

Phase 2 (next): parse a coach's CSV into the same structured-workout shape and generate
one Garmin workout per plan/session automatically.

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
  `cooldown_step`, `rest_step` (lap-button), `swim_repeat` ("N Times" block), and
  `build_swim_workout` to assemble a full `SwimmingWorkout`.
- `scripts/create_test_workout.py` — builds the sample 1000m workout above and pushes it
  to Garmin Connect + the last-used device. Good smoke test after any change to
  `swim_workout.py` or `client.py`.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in GARMIN_EMAIL / GARMIN_PASSWORD
.venv/bin/python scripts/create_test_workout.py
```

(This machine's system Python had no `pip`; the venv had to be created with
`python3 -m venv --without-pip .venv` and pip bootstrapped via
`get-pip.py` — see git history if that's needed again elsewhere.)

## Next up (phase 2)

Parse a coach's CSV into the same step/repeat structure `swim_workout.py` already builds,
and generate a workout per session. Still open:

- The actual CSV column layout/format the coach uses — no sample seen yet.
- How a plan maps to a Garmin workout: one workout per row, per day, per week? Multiple
  sets/repeats per session?
- Whether to auto-schedule the generated workout onto a calendar date
  (`Garmin.schedule_workout()` exists in the library) or just upload it to the library for
  manual scheduling.
