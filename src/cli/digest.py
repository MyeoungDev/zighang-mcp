from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Sequence, TextIO

from src.mcp.tools.jobs import daily_job_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Zighang daily job digest once.")
    parser.add_argument("--resume-profile-id", default="default", help="Resume profile ID to use. Default: default")
    parser.add_argument("--limit-per-profile", type=int, default=5, help="Maximum recommendations per filter profile. Default: 5")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top jobs in the digest summary. Default: 5")
    parser.add_argument("--include-seen", action="store_true", help="Include jobs already marked as seen.")
    parser.add_argument("--dry-run", action="store_true", help="Generate the digest without sending webhook or email notifications.")
    parser.add_argument("--json", action="store_true", help="Print the full result as JSON.")
    return parser


def _summary(result: dict[str, Any], meta: dict[str, Any]) -> str:
    lines = [
        f"started_at={meta['started_at']}",
        f"finished_at={meta['finished_at']}",
        f"duration_seconds={meta['duration_seconds']}",
        f"report_path={result.get('report_path', '')}",
        f"notification_channel={result.get('notification_channel', '')}",
        f"notification_result={result.get('notification_result', '')}",
    ]
    return "\n".join(lines)


def run(argv: Sequence[str] | None = None, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    started_at = datetime.now().astimezone()
    try:
        result = daily_job_digest(
            resume_profile_id=args.resume_profile_id,
            limit_per_profile=args.limit_per_profile,
            top_n=args.top_n,
            exclude_seen=not args.include_seen,
            send_notification=not args.dry_run,
        )
    except Exception as exc:
        print(f"zighang-digest failed: {exc.__class__.__name__}: {exc}", file=stderr)
        return 1

    finished_at = datetime.now().astimezone()
    meta = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
    }
    if args.json:
        print(json.dumps({**result, "run": meta}, ensure_ascii=False, indent=2, sort_keys=True), file=stdout)
    else:
        print(_summary(result, meta), file=stdout)
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(run(argv))


if __name__ == "__main__":
    main()
