"""Deterministic NVIDIA NIM multimodal benchmark.

The API key is never stored in this file. Set NVIDIA_API_KEY in the process
environment before running. Generated questions and reports are written under
tests/nvidia_benchmark_output/.
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


API_URL = os.environ.get(
    "NVIDIA_INVOKE_URL",
    "https://integrate.api.nvidia.com/v1/chat/completions",
)
MODEL = os.environ.get("NVIDIA_MODEL", "google/gemma-4-31b-it")
OUTPUT_DIR = Path(__file__).resolve().parent / "nvidia_benchmark_output"
WIDTH, HEIGHT = 960, 540
ENABLE_THINKING = os.environ.get("NVIDIA_ENABLE_THINKING", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_TOKENS = max(64, int(os.environ.get("NVIDIA_MAX_TOKENS", "16384")))
TEMPERATURE = float(os.environ.get("NVIDIA_TEMPERATURE", "1"))
TOP_P = float(os.environ.get("NVIDIA_TOP_P", "0.95"))
REPORT_LABEL = re.sub(
    r"[^A-Za-z0-9_-]+",
    "_",
    os.environ.get("NVIDIA_BENCHMARK_LABEL", "thinking"),
).strip("_") or "benchmark"


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        if bold
        else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


TITLE_FONT = font(30, True)
BODY_FONT = font(24)
OPTION_FONT = font(22)
SMALL_FONT = font(18)


def canvas(title: str):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 62), fill="#2457A6")
    draw.text((28, 14), title, fill="white", font=TITLE_FONT)
    draw.rectangle((0, HEIGHT - 34, WIDTH, HEIGHT), fill="#EFF2F6")
    draw.text((28, HEIGHT - 29), "课堂互动 · 图片题", fill="#667085", font=SMALL_FONT)
    return image, draw


def options(draw, values, x=540, y=125, gap=62):
    for index, value in enumerate(values):
        draw.rounded_rectangle(
            (x, y + index * gap, 910, y + index * gap + 44),
            radius=8,
            fill="#F5F7FA",
            outline="#CDD5DF",
        )
        draw.text((x + 14, y + index * gap + 8), value, fill="#172B4D", font=OPTION_FONT)


def save_jpeg(image: Image.Image, name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.jpg"
    image.save(path, format="JPEG", quality=80, optimize=True)
    return path


def build_questions():
    questions = []

    image, draw = canvas("数据统计")
    draw.text((35, 82), "图中数值最大的项目是？", fill="#111827", font=BODY_FONT)
    values = [12, 28, 19, 23]
    colors = ["#60A5FA", "#34D399", "#FBBF24", "#F87171"]
    for index, (value, color) in enumerate(zip(values, colors)):
        x = 55 + index * 105
        height = value * 8
        draw.rectangle((x, 430 - height, x + 60, 430), fill=color)
        draw.text((x + 15, 436), "ABCD"[index], fill="#111827", font=SMALL_FONT)
        draw.text((x + 13, 400 - height), str(value), fill="#111827", font=SMALL_FONT)
    options(draw, ["A. A项目", "B. B项目", "C. C项目", "D. D项目"])
    questions.append(("01_bar_chart", save_jpeg(image, "01_bar_chart"), "B"))

    image, draw = canvas("平面几何")
    draw.text((35, 82), "根据图形计算长方形面积。", fill="#111827", font=BODY_FONT)
    draw.rectangle((90, 175, 420, 365), outline="#2563EB", width=5)
    draw.text((225, 375), "8 cm", fill="#111827", font=BODY_FONT)
    draw.text((18, 255), "5 cm", fill="#111827", font=BODY_FONT)
    options(draw, ["A. 13 cm²", "B. 26 cm²", "C. 40 cm²", "D. 80 cm²"])
    questions.append(("02_geometry", save_jpeg(image, "02_geometry"), "C"))

    image, draw = canvas("月度销量表")
    draw.text((35, 82), "与上月相比，销量增量最大的月份是？", fill="#111827", font=BODY_FONT)
    rows = [("1月", 120), ("2月", 150), ("3月", 180), ("4月", 260)]
    draw.rectangle((55, 145, 440, 390), outline="#64748B", width=2)
    draw.line((220, 145, 220, 390), fill="#64748B", width=2)
    for row in range(1, 4):
        draw.line((55, 145 + row * 61, 440, 145 + row * 61), fill="#CBD5E1", width=2)
    for index, (month, value) in enumerate(rows):
        draw.text((105, 161 + index * 61), month, fill="#111827", font=OPTION_FONT)
        draw.text((295, 161 + index * 61), str(value), fill="#111827", font=OPTION_FONT)
    options(draw, ["A. 1月", "B. 2月", "C. 3月", "D. 4月"])
    questions.append(("03_table", save_jpeg(image, "03_table"), "D"))

    image, draw = canvas("C 语言程序阅读")
    draw.text((35, 82), "下列程序输出什么？", fill="#111827", font=BODY_FONT)
    code = ["int s = 0;", "for (int i=1; i<=4; i++)", "    s += i * i;", 'printf("%d", s);']
    draw.rounded_rectangle((45, 135, 490, 400), radius=12, fill="#111827")
    for index, line in enumerate(code):
        draw.text((68, 158 + index * 52), line, fill="#E5E7EB", font=OPTION_FONT)
    options(draw, ["A. 20", "B. 30", "C. 32", "D. 54"])
    questions.append(("04_code", save_jpeg(image, "04_code"), "B"))

    image, draw = canvas("视觉计数")
    draw.text((35, 82), "图中共有多少个蓝色三角形？", fill="#111827", font=BODY_FONT)
    triangles = [(90, 175), (220, 175), (350, 175)]
    for x, y in triangles:
        draw.polygon([(x, y + 90), (x + 48, y), (x + 96, y + 90)], fill="#2563EB")
    draw.ellipse((120, 330, 205, 415), fill="#EF4444")
    draw.ellipse((270, 330, 355, 415), fill="#2563EB")
    options(draw, ["A. 2个", "B. 3个", "C. 4个", "D. 5个"])
    questions.append(("05_visual_count", save_jpeg(image, "05_visual_count"), "B"))

    image, draw = canvas("折线图读取")
    draw.text((35, 82), "当 x=3 时，图中 y 的值是多少？", fill="#111827", font=BODY_FONT)
    origin = (85, 420)
    draw.line((origin[0], 140, origin[0], origin[1]), fill="#111827", width=3)
    draw.line((origin[0], origin[1], 470, origin[1]), fill="#111827", width=3)
    points = [(1, 3), (2, 5), (3, 7), (4, 6)]
    pixels = []
    for x, y in points:
        px, py = origin[0] + x * 85, origin[1] - y * 36
        pixels.append((px, py))
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill="#DC2626")
        draw.text((px - 5, origin[1] + 8), str(x), fill="#111827", font=SMALL_FONT)
    draw.line(pixels, fill="#DC2626", width=4)
    options(draw, ["A. 3", "B. 5", "C. 7", "D. 9"])
    questions.append(("06_line_graph", save_jpeg(image, "06_line_graph"), "C"))

    return questions


def parse_answer(text: str):
    candidates = re.findall(r"\{[\s\S]*?\}", text or "")
    for candidate in reversed(candidates):
        try:
            payload = json.loads(candidate)
            answers = payload.get("answers")
            if isinstance(answers, list) and answers:
                return str(answers[0]).strip().upper()
        except Exception:
            pass
    match = re.search(r"\b([A-D])\b", text or "", re.I)
    return match.group(1).upper() if match else ""


def invoke(api_key: str, image_path: Path):
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "这是课堂单选题截图。请读取题干、图表和选项并解题。"
                            '只输出合法 JSON：{"answers":["A"]}，不要输出其他文字。'
                        ),
                    },
                ],
            }
        ],
        "model": MODEL,
        "chat_template_kwargs": {"enable_thinking": ENABLE_THINKING},
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }
    started = time.perf_counter()
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        json=payload,
        timeout=(15, 240),
    )
    elapsed = time.perf_counter() - started
    request_id = (
        response.headers.get("x-request-id")
        or response.headers.get("nvcf-reqid")
        or response.headers.get("request-id")
        or ""
    )
    response.raise_for_status()
    data = response.json()
    content = str(data["choices"][0]["message"].get("content") or "")
    usage = data.get("usage") or {}
    return {
        "elapsed_seconds": round(elapsed, 3),
        "request_id": request_id,
        "content": content,
        "usage": usage,
        "finish_reason": data["choices"][0].get("finish_reason"),
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
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("NVIDIA_API_KEY is required")
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
                f"correct={row['correct']} time={row['elapsed_seconds']:.3f}s"
            )
        except Exception as exc:
            row.update({"actual": "", "correct": False, "error": str(exc)})
            print(f"{name}: ERROR {exc}")
        results.append(row)

    completed = [row for row in results if "elapsed_seconds" in row]
    times = [row["elapsed_seconds"] for row in completed]
    correct_count = sum(1 for row in completed if row["correct"])
    summary = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "endpoint": API_URL,
        "model": MODEL,
        "parameters": {
            "enable_thinking": ENABLE_THINKING,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "stream": False,
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
        "results": results,
    }
    report_path = OUTPUT_DIR / f"report_{REPORT_LABEL}.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False, indent=2))
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
