from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 20:
        raise ValueError("The benchmark manifest must contain exactly 20 cases.")

    seen: set[str] = set()
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("Every case must have a unique, non-empty case_id.")
        seen.add(case_id)
        for field in ("title", "task_description", "repository_url", "acceptance_criteria"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"{case_id}: '{field}' must be populated before evaluation.")
        if "example.com/your" in case["repository_url"].lower():
            raise ValueError(f"{case_id}: replace the repository URL placeholder.")
    return payload


async def run_case(
    client: httpx.AsyncClient,
    base_url: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "title": case["title"],
        "status": "error",
        "task_id": None,
        "run_id": None,
        "duration_seconds": None,
        "error": None,
        "acceptance_criteria": case["acceptance_criteria"],
    }

    try:
        task_response = await client.post(
            f"{base_url}/api/v1/tasks",
            json={
                "title": case["title"],
                "description": case["task_description"],
                "repository_url": case["repository_url"],
            },
        )
        task_response.raise_for_status()
        task = task_response.json()
        result["task_id"] = task["id"]

        run_response = await client.post(
            f"{base_url}/api/v1/tasks/{task['id']}/runs",
        )
        run_response.raise_for_status()
        run = run_response.json()
        result["run_id"] = run.get("id")
        result["status"] = str(run.get("status", "unknown")).lower()

    except httpx.HTTPStatusError as exc:
        result["status"] = "http_error"
        result["error"] = (
            f"HTTP {exc.response.status_code}: "
            f"{exc.response.text[:1000]}"
        )
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["duration_seconds"] = round(time.perf_counter() - started, 2)
    return result


async def main_async(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    base_url = args.base_url.rstrip("/")
    headers = {}
    token = args.token or os.getenv("FORGEAI_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = httpx.Timeout(args.timeout, connect=20.0)
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        results = []
        for index, case in enumerate(manifest["cases"], start=1):
            print(f"[{index:02d}/20] {case['case_id']} — {case['title']}", flush=True)
            result = await run_case(client, base_url, case)
            results.append(result)
            print(
                f"       status={result['status']} "
                f"duration={result['duration_seconds']}s",
                flush=True,
            )

    succeeded = sum(item["status"] == "succeeded" for item in results)
    awaiting_approval = sum(
        item["status"] in {"awaiting_approval", "pending", "executing"}
        for item in results
    )
    failed = len(results) - succeeded - awaiting_approval

    report = {
        "benchmark_name": manifest.get("benchmark_name", "ForgeAI Evaluation"),
        "generated_at": datetime.now(UTC).isoformat(),
        "total_cases": len(results),
        "succeeded": succeeded,
        "awaiting_approval_or_nonterminal": awaiting_approval,
        "failed_or_error": failed,
        "workflow_success_rate_percent": round(succeeded / len(results) * 100, 2),
        "results": results,
        "interpretation": (
            "This measures workflow terminal status only. It does not independently "
            "prove patch correctness. Review each sandbox test result and acceptance "
            "criteria before reporting a code-quality success rate."
        ),
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== ForgeAI benchmark summary ===")
    print(f"Total cases: {len(results)}")
    print(f"Succeeded: {succeeded}")
    print(f"Awaiting approval/nonterminal: {awaiting_approval}")
    print(f"Failed/errors: {failed}")
    print(f"Workflow success rate: {report['workflow_success_rate_percent']}%")
    print(f"Report: {report_path.resolve()}")
    print("\nNote: workflow status is not a substitute for verifying patch correctness.")
    return 0 if succeeded == len(results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the 20-case ForgeAI benchmark.")
    parser.add_argument("--base-url", default=os.getenv("FORGEAI_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=None)
    parser.add_argument("--manifest", default="tests/evaluation/benchmark_tasks.json")
    parser.add_argument("--report", default="artifacts/evaluation/benchmark_report.json")
    parser.add_argument("--timeout", type=float, default=1800.0)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main_async(parse_args())))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Evaluation setup error: {exc}", file=sys.stderr)
        raise SystemExit(2)
