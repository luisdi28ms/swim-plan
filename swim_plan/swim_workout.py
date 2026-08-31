"""Build pool-swim structured workouts for Garmin Connect.

Fills in the pool-specific parts (poolLength, stroke type, lap-button rest)
that garminconnect's SwimmingWorkout/ExecutableStep models leave as generic
dict fields, using the field names Garmin Connect's workout-service expects.
"""

from __future__ import annotations

from garminconnect.workout import (
    ConditionType,
    ExecutableStep,
    RepeatGroup,
    SportType,
    StepType,
    SwimmingWorkout,
    TargetType,
    WorkoutSegment,
    create_repeat_group,
)

POOL_LENGTH_UNIT_METER = {"unitId": 1, "unitKey": "meter", "factor": 100}

NO_TARGET = {
    "workoutTargetTypeId": TargetType.NO_TARGET,
    "workoutTargetTypeKey": "no.target",
    "displayOrder": 1,
}

# strokeTypeId values as used by Garmin Connect's workout-service.
STROKE_TYPES = {
    "free": {"strokeTypeId": 6, "strokeTypeKey": "free", "displayOrder": 6},
    "backstroke": {"strokeTypeId": 2, "strokeTypeKey": "backstroke", "displayOrder": 2},
    "breaststroke": {"strokeTypeId": 3, "strokeTypeKey": "breaststroke", "displayOrder": 3},
    "fly": {"strokeTypeId": 5, "strokeTypeKey": "fly", "displayOrder": 5},
    "choice": {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0},
}

NO_STROKE = STROKE_TYPES["choice"]
NO_EQUIPMENT = {"equipmentTypeId": 0, "displayOrder": 0}

# equipmentTypeId values as used by Garmin Connect's workout-service.
EQUIPMENT_TYPES = {
    "fins": {"equipmentTypeId": 1, "equipmentTypeKey": "fins", "displayOrder": 1},
    "kickboard": {"equipmentTypeId": 2, "equipmentTypeKey": "kickboard", "displayOrder": 2},
    "paddles": {"equipmentTypeId": 3, "equipmentTypeKey": "paddles", "displayOrder": 3},
    "pull_buoy": {"equipmentTypeId": 4, "equipmentTypeKey": "pull_buoy", "displayOrder": 4},
    "snorkel": {"equipmentTypeId": 5, "equipmentTypeKey": "snorkel", "displayOrder": 5},
}


def _distance_step(
    distance_meters: float,
    step_order: int,
    stroke: str,
    step_type_id: int,
    step_type_key: str,
    display_order: int,
    equipment: str | None = None,
    note: str | None = None,
) -> ExecutableStep:
    kwargs = {"description": note} if note else {}
    return ExecutableStep(
        stepOrder=step_order,
        stepType={"stepTypeId": step_type_id, "stepTypeKey": step_type_key, "displayOrder": display_order},
        endCondition={
            "conditionTypeId": ConditionType.DISTANCE,
            "conditionTypeKey": "distance",
            "displayOrder": 3,
            "displayable": True,
        },
        endConditionValue=float(distance_meters),
        preferredEndConditionUnit=POOL_LENGTH_UNIT_METER,
        targetType=NO_TARGET,
        strokeType=STROKE_TYPES.get(stroke, NO_STROKE),
        equipmentType=EQUIPMENT_TYPES.get(equipment, NO_EQUIPMENT) if equipment else NO_EQUIPMENT,
        **kwargs,
    )


def swim_step(
    distance_meters: float,
    step_order: int,
    stroke: str = "choice",
    equipment: str | None = None,
    note: str | None = None,
) -> ExecutableStep:
    """A distance-based swim step, e.g. "4 x 100m free" or "50m choice w/ fins"."""
    return _distance_step(distance_meters, step_order, stroke, StepType.INTERVAL, "interval", 3, equipment, note)


def warmup_step(
    distance_meters: float,
    step_order: int,
    stroke: str = "choice",
    equipment: str | None = None,
    note: str | None = None,
) -> ExecutableStep:
    """A distance-based warmup step, e.g. "600m choice"."""
    return _distance_step(distance_meters, step_order, stroke, StepType.WARMUP, "warmup", 1, equipment, note)


def cooldown_step(
    distance_meters: float,
    step_order: int,
    stroke: str = "choice",
    equipment: str | None = None,
    note: str | None = None,
) -> ExecutableStep:
    """A distance-based cooldown step."""
    return _distance_step(distance_meters, step_order, stroke, StepType.COOLDOWN, "cooldown", 2, equipment, note)


def rest_step(step_order: int) -> ExecutableStep:
    """An untimed rest step ended by pressing the lap button, as in the screenshot."""
    return ExecutableStep(
        stepOrder=step_order,
        stepType={"stepTypeId": StepType.REST, "stepTypeKey": "rest", "displayOrder": 5},
        endCondition={
            "conditionTypeId": ConditionType.LAP_BUTTON,
            "conditionTypeKey": "lap.button",
            "displayOrder": 1,
            "displayable": True,
        },
        endConditionValue=None,
        targetType=NO_TARGET,
        strokeType=NO_STROKE,
        equipmentType=NO_EQUIPMENT,
    )


def timed_rest_step(seconds: float, step_order: int) -> ExecutableStep:
    """A fixed-duration rest step, e.g. the "sp" (segundos de pausa) rest in the plan."""
    return ExecutableStep(
        stepOrder=step_order,
        stepType={"stepTypeId": StepType.REST, "stepTypeKey": "rest", "displayOrder": 5},
        endCondition={
            "conditionTypeId": ConditionType.TIME,
            "conditionTypeKey": "time",
            "displayOrder": 2,
            "displayable": True,
        },
        endConditionValue=float(seconds),
        targetType=NO_TARGET,
        strokeType=NO_STROKE,
        equipmentType=NO_EQUIPMENT,
    )


def swim_repeat(
    iterations: int,
    distance_meters: float,
    step_order: int,
    stroke: str = "choice",
    rest_between: bool = True,
) -> RepeatGroup:
    """"N Times" block of a swim step (+ a lap-button rest) as seen in the screenshot."""
    inner: list[ExecutableStep] = [swim_step(distance_meters, step_order + 1, stroke)]
    if rest_between:
        inner.append(rest_step(step_order + 2))
    return create_repeat_group(iterations, inner, step_order)


def build_swim_workout(
    name: str,
    steps: list[ExecutableStep | RepeatGroup],
    pool_length_meters: float = 25.0,
    description: str | None = None,
) -> SwimmingWorkout:
    """Assemble a SwimmingWorkout with pool length set at workout and segment level."""
    pool_length = {"poolLength": pool_length_meters, "poolLengthUnit": POOL_LENGTH_UNIT_METER}
    segment = WorkoutSegment(
        segmentOrder=1,
        sportType={
            "sportTypeId": SportType.SWIMMING,
            "sportTypeKey": "swimming",
            "displayOrder": 3,
        },
        workoutSteps=steps,
        **pool_length,
    )
    return SwimmingWorkout(
        workoutName=name,
        description=description,
        estimatedDurationInSecs=0,
        workoutSegments=[segment],
        **pool_length,
    )
