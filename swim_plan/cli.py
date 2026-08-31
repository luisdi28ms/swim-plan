"""swim-plan CLI: turn a JSON workout spec into a Garmin Connect workout.

Run as ``python -m swim_plan``. Commands:

    create SPEC [--push | --dry-run]   build from a spec file; upload; optionally push
    list [--limit N]                   list workouts in the Garmin Connect library
    delete WORKOUT_ID                  delete a workout from the library
    push WORKOUT_ID                    push an uploaded workout to the last-used device

``--dry-run`` prints the exact upload payload (the same ``to_dict()`` JSON
``upload_swimming_workout`` sends) and never touches the network, so specs
can be iterated on without spamming a real Garmin account.
"""

from __future__ import annotations

import argparse
import json
import sys

from swim_plan.spec import SpecError, build_workout_from_spec, load_spec, total_distance_meters


def _client():
    # Import lazily so --dry-run works without garmin credentials configured.
    from dotenv import load_dotenv

    from swim_plan.client import get_client

    load_dotenv()
    return get_client()


def _cmd_create(args: argparse.Namespace) -> None:
    workout = build_workout_from_spec(load_spec(args.spec))
    payload = workout.to_dict()
    summary = (
        f"Workout '{payload['workoutName']}': {total_distance_meters(payload):g} m "
        f"in a {payload['poolLength']:g} m pool"
    )
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"Dry run only. {summary}. Nothing was uploaded.", file=sys.stderr)
        return

    print(f"{summary}. Uploading...")
    client = _client()
    result = client.upload_swimming_workout(workout)
    workout_id = result.get("workoutId") or result.get("id")
    print(f"Uploaded workout id={workout_id}: {result.get('workoutName')}")
    if args.push:
        push_result = client.push_workout_to_device(workout_id=workout_id)
        print(f"Pushed workout {workout_id} to the last-used device: {push_result}")


def _cmd_list(args: argparse.Namespace) -> None:
    workouts = _client().get_workouts(limit=args.limit)
    if not workouts:
        print("No workouts in the library.")
        return
    for workout in workouts:
        sport = (workout.get("sportType") or {}).get("sportTypeKey", "?")
        print(f"{workout.get('workoutId')}\t{sport}\t{workout.get('workoutName')}")


def _cmd_delete(args: argparse.Namespace) -> None:
    _client().delete_workout(args.workout_id)
    print(f"Deleted workout {args.workout_id} from the Garmin Connect library.")


def _cmd_push(args: argparse.Namespace) -> None:
    result = _client().push_workout_to_device(workout_id=args.workout_id)
    print(f"Pushed workout {args.workout_id} to the last-used device: {result}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m swim_plan",
        description="Build, upload, and push Garmin pool-swim workouts from JSON spec files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="build a workout from a spec file and upload it")
    create.add_argument("spec", help="path to the JSON workout spec (see examples/)")
    mode = create.add_mutually_exclusive_group()
    mode.add_argument("--push", action="store_true", help="also push to the last-used device after upload")
    mode.add_argument(
        "--dry-run", action="store_true", help="print the upload payload and exit; no network calls"
    )
    create.set_defaults(func=_cmd_create)

    list_cmd = sub.add_parser("list", help="list workouts in the Garmin Connect library")
    list_cmd.add_argument("--limit", type=int, default=100, help="max workouts to list (default 100)")
    list_cmd.set_defaults(func=_cmd_list)

    delete = sub.add_parser("delete", help="delete a workout from the library by id")
    delete.add_argument("workout_id", help="workout id (see 'list')")
    delete.set_defaults(func=_cmd_delete)

    push = sub.add_parser("push", help="push an already-uploaded workout to the last-used device")
    push.add_argument("workout_id", help="workout id (see 'list')")
    push.set_defaults(func=_cmd_push)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SpecError as exc:
        parser.exit(2, f"Spec error: {exc}\n")


if __name__ == "__main__":
    main()
