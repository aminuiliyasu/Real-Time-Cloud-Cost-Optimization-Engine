import argparse
import json
import time
from datetime import datetime, timezone

from app.workers.jobs import run_ingestion_cycle


def run_once(hours: int) -> dict:
    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        **run_ingestion_cycle(hours=hours),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run periodic background jobs for ingestion and rule evaluation.")
    parser.add_argument("--hours", type=int, default=24, help="Metric ingestion window size in hours.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=900,
        help="How often to run jobs in loop mode.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single cycle and exit.",
    )
    args = parser.parse_args()

    if args.hours <= 0:
        raise SystemExit("--hours must be > 0")
    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds must be > 0")

    if args.run_once:
        print(json.dumps(run_once(hours=args.hours), indent=2))
        return

    while True:
        print(json.dumps(run_once(hours=args.hours), indent=2))
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
