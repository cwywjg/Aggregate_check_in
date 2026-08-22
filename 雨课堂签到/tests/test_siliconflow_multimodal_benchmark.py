"""Deterministic SiliconFlow Qwen multimodal benchmark.

The API key is read only from SILICONFLOW_API_KEY and is never written to the
source, report, logs or generated images.
"""

from __future__ import annotations

import base64
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
from test_nvidia_multimodal_benchmark import build_questions, parse_answer  # noqa: E402


API_URL = os.environ.get(
    "SILICONFLOW_INVOKE_URL",
    "https://api.siliconflow.cn/v1/chat/completions",
)
MODEL = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen3.5-27B")
OUTPUT_DIR = TESTS_DIR / "siliconflow_benchmark_output"
ENABLE_THINKING = os.environ.get("SILICONFLOW_ENABLE_THINKING", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
IMAGE_DETAIL = os.environ.get("SILICONFLOW_IMAGE_DETAIL", "low").strip().lower()
if IMAGE_DETAIL not in {"low", "high", "auto"}:
    IMAGE_DETAIL = "low"
MAX_TOKENS = max(64, int(os.environ.get("SILICONFLOW_MAX_TOKENS", "256")))


def invoke(api_key: str, image_path: Path):
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded}",
                            "detail": IMAGE_DETAIL,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "这是课堂单选题截图。请读取题干、图表和选项并解题。"
                            "必须逐字核对数字、运算符、循环边界和图表刻度，"
                            "独立计算后再用选项反向复核，禁止猜测。"
                            '只输出合法 JSON：{"answers":["A"]}，不要输出其他文字。'
                        ),
                    },
                ],
            }
        ],
        "enable_thinking": ENABLE_THINKING,
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "temperature": 0.1,
        "top_p": 0.7,
        "response_format": {"type": "json_object"},
    }
    started = time.perf_counter()
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        json=payload,
        timeout=(15, 180),
    )
    elapsed = time.perf_counter() - started
    request_id = (
        response.headers.get("x-siliconcloud-trace-id")
        or response.headers.get("x-request-id")
        or response.headers.get("request-id")
        or ""
    )
    response.raise_for_status()
    data = response.json()
    content = str(data["choices"][0]["message"].get("content") or "")
    return {
        "elapsed_seconds": round(elapsed, 3),
        "request_id": request_id,
        "content": content,
        "usage": data.get("usage") or {},
        "finish_reason": data["choices"][0].get("finish_reason"),
        "response_model": data.get("model") or MODEL,
    }


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return 0
    index = (len(ordered) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def main():
    api_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("SILICONFLOW_API_KEY is required")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().astimezone()
    results = []
    for name, image_path, expected in build_questions():
        row = {
            "name": name,
            "image": str(image_path),
            "image_bytes": image_path.stat().st_size,
            "expected": expected,
        }
        try:
            row.update(invoke(api_key, image_path))
            row["actual"] = parse_answer(row["content"])
            row["correct"] = row["actual"] == expected
            print(
                f"{name}: expected={expected} actual={row['actual'] or '-'} "
                f"correct={row['correct']} time={row['elapsed_seconds']:.3f}s",
                flush=True,
            )
        except Exception as exc:
            row.update({"actual": "", "correct": False, "error": str(exc)})
            print(f"{name}: ERROR {exc}", flush=True)
        results.append(row)

    completed = [row for row in results if "elapsed_seconds" in row]
    times = [row["elapsed_seconds"] for row in completed]
    correct_count = sum(1 for row in completed if row["correct"])
    usage_totals = {}
    for row in completed:
        for key, value in (row.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                usage_totals[key] = usage_totals.get(key, 0) + value
    summary = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "endpoint": API_URL,
        "model": MODEL,
        "parameters": {
            "enable_thinking": ENABLE_THINKING,
            "image_detail": IMAGE_DETAIL,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.1,
            "top_p": 0.7,
            "stream": False,
            "json_mode": True,
        },
        "total": len(results),
        "completed": len(completed),
        "correct": correct_count,
        "accuracy": round(correct_count / len(completed), 4) if completed else 0,
        "latency_seconds": {
            "min": round(min(times), 3) if times else 0,
            "max": round(max(times), 3) if times else 0,
            "mean": round(statistics.mean(times), 3) if times else 0,
            "median": round(statistics.median(times), 3) if times else 0,
            "p95": round(percentile(times, 0.95), 3) if times else 0,
        },
        "usage_totals": usage_totals,
        "results": results,
    }
    report_path = OUTPUT_DIR / "report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "results"},
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    print(f"report={report_path}", flush=True)


if __name__ == "__main__":
    main()
