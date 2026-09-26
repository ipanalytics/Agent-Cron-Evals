"""agent-cron-evals — say which scheduled jobs are dead, and stay quiet when none are.

Designed for the no-model cron pattern: the text it prints goes straight into a message, so a
healthy run prints nothing at all and a broken one prints one line per problem.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime

from . import checks, report
from . import config as config_mod
from . import jobs as jobs_mod


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-cron-evals",
        description="Check that scheduled agent jobs actually ran, and that their output arrived.",
    )
    parser.add_argument(
        "--config", required=True, help="JSON file listing the jobs that must be alive"
    )
    parser.add_argument("--jobs", help="job list to read (default: jobs_file from the config)")
    parser.add_argument(
        "--output", help="where to write the JSON record (default: from the config)"
    )
    parser.add_argument(
        "--json", action="store_true", help="print the whole record, not just problems"
    )
    parser.add_argument(
        "--all", action="store_true", help="print every check, healthy ones included"
    )
    parser.add_argument("--quiet", action="store_true", help="write the record and print nothing")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        conf = config_mod.load(args.config)
    except (OSError, ValueError) as exc:
        print(f"agent-cron-evals: {exc}", file=sys.stderr)
        return 2

    jobs_path = config_mod.expand(args.jobs or conf.get("jobs_file") or "~/.hermes/cron/jobs.json")
    try:
        jobs_map = jobs_mod.load(jobs_path)
    except (OSError, ValueError) as exc:
        print(f"agent-cron-evals: cannot read the job list at {jobs_path}: {exc}", file=sys.stderr)
        return 2

    now = time.time()
    moment = datetime.now(UTC)
    result = checks.run(conf, jobs_map, now, moment.hour, moment.weekday())
    target = report.write(conf, result, now, args.output)

    if args.quiet:
        return 0
    if args.json:
        print(json.dumps(report.payload(result, now), ensure_ascii=False, indent=1))
        return 0
    if args.all:
        for finding in result.findings:
            line = f"{finding.state:4} {finding.name} ({finding.job})"
            if finding.detail:
                line += f" — {finding.detail}"
            print(line)
        print(report.summary_line(result))
    for text in report.lines(result):
        print(text)
    if not result.problems and args.all:
        print(f"(no problems; record written to {target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
