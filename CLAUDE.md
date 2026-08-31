# Swim workout acronym glossary

Use this table to translate Spanish swim-plan acronyms into Garmin workout steps.

| Acronym | Meaning (Spanish) | Meaning (English) |
|---|---|---|
| sp | Segundos de pausa | Seconds of rest |
| TD | Trabajo - descanso | Work - rest |
| BL | Brazadas largas | Long strokes |
| VL | Vueltas largas | Long turns/laps |
| c/e | Cada estilo | Each stroke |
| Opt | Optativo | Optional |
| Esp | Especialidad (mejor estilo) | Specialty (best stroke) |
| ED | Estilo débil | Weak stroke |
| BB | Bajando brazadas | Descending strokes |
| CI | Combinado | Combined/medley |
| ap | Apnea | Breath-holding |
| VE | Variando estilos | Varying strokes |
| pb | pull buoy | Pull buoy |
| patas | Uso de aletas (fins) | Fins — tag the step(s) with `equipment="fins"` |

# Garmin workout-service field reference

Values confirmed working against the real Garmin Connect API (via `swim_plan/swim_workout.py`).

## equipmentTypeId (swim equipment)
| id | key | meaning |
|---|---|---|
| 0 | none | no equipment |
| 1 | fins | fins (aletas / patas) |
| 2 | kickboard | kickboard |
| 3 | paddles | paddles (manoplas) |
| 4 | pull_buoy | pull buoy (pb) |
| 5 | snorkel | snorkel |

## strokeTypeId (as used by this project's `STROKE_TYPES` in `swim_workout.py`)
`free=6, backstroke=2, breaststroke=3, fly=5, choice=0`. Use `"choice"` when the plan doesn't
name a specific stroke, including kick-only work (there is no dedicated "kick" stroke type).

## Notes vs. description — where CSV text goes
Garmin has two separate free-text fields, and they must not be mixed up:
- **Workout-level `description`** (on `SwimmingWorkout`/`build_swim_workout`): a short label
  for the whole workout only (e.g. "Serie 2 - Semana de fondo (24-28 Ago)"). Never put
  set-specific instructions here.
- **Per-step `description`** (pass `note=...` to `swim_step`/`warmup_step`/`cooldown_step`):
  any instruction that is specific to one step/rep and isn't already captured by
  distance + stroke + equipment. This is what the Garmin Connect app/watch shows as the
  step's own note.

Rule of thumb when reading a CSV cell: if the cell has a compound instruction beyond
"distance + stroke [+ equipment]" — e.g. "25 pat flecha - 75L nad" (partial-distance
instruction within one rep), "vel" (go at speed/effort), "suave" (easy effort), "VE"
(varying strokes), a technique cue, etc. — attach it as a per-step `note`, not to the
workout's overall description. The workout description should stay a one-line label.

## Known simplifications (not yet modeled)
- No timed-rest-with-note combo helper — `rest_step` (lap button) and `timed_rest_step`
  (fixed seconds) exist separately, neither takes a `note` yet.
- No pace/effort target types wired up — "vel" (speed) and "suave" (easy) are represented
  only via `note` text, not an actual Garmin pace/intensity target.
- Partial-distance instructions within a single rep (e.g. "25 pat flecha - 75L nad" inside
  one 100m rep) are NOT split into two Garmin steps — they stay one step with a `note`
  describing the split, since Garmin steps are single distance/stroke/equipment units.
