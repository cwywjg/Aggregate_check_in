"""
雨课堂 AI 自动答题 — 真实场景模拟测试（含课件截图多模态）
在服务器上运行，使用 Pillow 生成模拟 PPT 课件截图，测试 Gemini 多模态识图能力。

运行前确保安装依赖:
    pip install google-genai Pillow
"""

import json
import time
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_solver import solve_yuketang_problem

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  未安装 Pillow，将跳过图片生成。安装命令: pip install Pillow")


# ==================== 工具函数 ====================

def get_font(size=28):
    """尝试加载中文字体，失败则使用默认字体"""
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",      # Ubuntu 文泉驿
        "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",         # CentOS
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf",
        "C:/Windows/Fonts/msyh.ttc",                          # Windows 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",                        # Windows 黑体
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_slide_image(title, lines, width=960, height=540, bg_color="#FFFFFF"):
    """生成模拟 PPT 课件截图"""
    if not HAS_PIL:
        return None

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    title_font = get_font(32)
    body_font = get_font(24)
    small_font = get_font(18)

    # 顶部蓝色标题栏
    draw.rectangle([(0, 0), (width, 60)], fill="#2B579A")
    draw.text((30, 14), title, fill="white", font=title_font)

    # 底部灰色信息栏
    draw.rectangle([(0, height - 35), (width, height)], fill="#E8E8E8")
    draw.text((30, height - 30), "雨课堂 · 课堂互动", fill="#888", font=small_font)
    draw.text((width - 200, height - 30), "2024-2025 学年", fill="#888", font=small_font)

    # 内容区域
    y = 85
    for line in lines:
        if line.startswith("##"):
            # 加粗标题行
            draw.text((40, y), line[2:].strip(), fill="#333", font=title_font)
            y += 48
        elif line.startswith("---"):
            draw.line([(40, y + 5), (width - 40, y + 5)], fill="#CCC", width=1)
            y += 15
        elif line.startswith("  "):
            # 选项缩进
            draw.text((70, y), line.strip(), fill="#444", font=body_font)
            y += 38
        else:
            draw.text((40, y), line, fill="#222", font=body_font)
            y += 38

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ==================== 模拟真实雨课堂题目（含图片） ====================

def build_test_problems():
    problems = []

    # ──────── 1. 单选：马原（纯文字，带课件截图） ────────
    slide_img = make_slide_image("马克思主义基本原理", [
        "## 第三章 唯物辩证法",
        "---",
        "课堂练习：",
        "",
        "唯物辩证法的实质和核心是（  ）",
        "",
        "  A. 质量互变规律",
        "  B. 对立统一规律",
        "  C. 否定之否定规律",
        "  D. 联系和发展的规律",
    ])
    problems.append({
        "name": "【马原】单选题 — 带课件截图",
        "problemType": 0,
        "body": "<p>唯物辩证法的实质和核心是（  ）</p>",
        "options": [
            {"key": "A", "value": "质量互变规律"},
            {"key": "B", "value": "对立统一规律"},
            {"key": "C", "value": "否定之否定规律"},
            {"key": "D", "value": "联系和发展的规律"}
        ],
        "image": slide_img,
        "expected": ["B"]
    })

    # ──────── 2. 单选：高数（公式题，图片是关键） ────────
    slide_img = make_slide_image("高等数学 A（上）", [
        "## 第二章 导数与微分",
        "---",
        "已知 f(x) = x³ - 3x² + 2x + 1",
        "",
        "求 f'(2) 的值",
        "",
        "  A. 2",
        "  B. 0",
        "  C. -2",
        "  D. 4",
        "",
        "提示：f'(x) = 3x² - 6x + 2",
    ])
    problems.append({
        "name": "【高数】单选 — 图片含解题提示",
        "problemType": 0,
        "body": "<p>已知 f(x) = x³ - 3x² + 2x + 1，求 f'(2) 的值</p>",
        "options": [
            {"key": "A", "value": "2"},
            {"key": "B", "value": "0"},
            {"key": "C", "value": "-2"},
            {"key": "D", "value": "4"}
        ],
        "image": slide_img,
        "expected": ["A"]
    })

    # ──────── 3. 单选：C语言（代码题） ────────
    slide_img = make_slide_image("C 语言程序设计", [
        "## 指针与数组",
        "---",
        "int a[] = {1, 2, 3, 4, 5};",
        "int *p = a + 2;",
        "printf(\"%d\", *(p + 1));",
        "",
        "程序的输出结果是？",
        "",
        "  A. 3",
        "  B. 4",
        "  C. 5",
        "  D. 2",
    ])
    problems.append({
        "name": "【C语言】单选 — 指针题",
        "problemType": 0,
        "body": "<pre>int a[] = {1,2,3,4,5};\nint *p = a + 2;\nprintf(\"%d\", *(p+1));</pre><p>程序输出？</p>",
        "options": [
            {"key": "A", "value": "3"},
            {"key": "B", "value": "4"},
            {"key": "C", "value": "5"},
            {"key": "D", "value": "2"}
        ],
        "image": slide_img,
        "expected": ["B"]
    })

    # ──────── 4. 纯图片题（body 为空，只靠图片识别） ────────
    slide_img = make_slide_image("线性代数", [
        "## 矩阵运算",
        "---",
        "判断以下说法哪个正确：",
        "",
        "矩阵 A = [[1,2],[3,4]]",
        "矩阵 B = [[0,1],[1,0]]",
        "",
        "求 AB 的迹 (trace) 为？",
        "",
        "  A. 5",
        "  B. 6",
        "  C. 7",
        "  D. 4",
    ])
    problems.append({
        "name": "【线代】纯图片题 — body 为空",
        "problemType": 0,
        "body": "",
        "options": [
            {"key": "A", "value": "5"},
            {"key": "B", "value": "6"},
            {"key": "C", "value": "7"},
            {"key": "D", "value": "4"}
        ],
        "image": slide_img,
        "expected": ["B"],
        "note": "★ body 为空，AI 只能依赖图片识别"
    })

    # ──────── 5. 多选题 ────────
    slide_img = make_slide_image("数据结构与算法", [
        "## 第六章 排序算法",
        "---",
        "以下哪些排序算法是稳定的？",
        "",
        "  A. 冒泡排序",
        "  B. 快速排序",
        "  C. 归并排序",
        "  D. 选择排序",
        "  E. 插入排序",
    ])
    problems.append({
        "name": "【数据结构】多选题 — 排序稳定性",
        "problemType": 1,
        "body": "<p>以下哪些排序算法是稳定的？</p>",
        "options": [
            {"key": "A", "value": "冒泡排序"},
            {"key": "B", "value": "快速排序"},
            {"key": "C", "value": "归并排序"},
            {"key": "D", "value": "选择排序"},
            {"key": "E", "value": "插入排序"}
        ],
        "image": slide_img,
        "expected": ["A", "C", "E"],
        "validate_sorted": True
    })

    # ──────── 6. 多选题（政治） ────────
    problems.append({
        "name": "【毛概】多选题 — 无图片",
        "problemType": 1,
        "body": "<p>新民主主义革命的三大法宝是（  ）</p>",
        "options": [
            {"key": "A", "value": "统一战线"},
            {"key": "B", "value": "武装斗争"},
            {"key": "C", "value": "土地革命"},
            {"key": "D", "value": "党的建设"}
        ],
        "image": None,
        "expected": ["A", "B", "D"],
        "validate_sorted": True
    })

    # ──────── 7. 投票题 ────────
    problems.append({
        "name": "【课堂互动】投票题",
        "problemType": 2,
        "body": "<p>你对本节课的内容掌握程度如何？</p>",
        "options": [
            {"key": "A", "value": "完全掌握"},
            {"key": "B", "value": "基本理解"},
            {"key": "C", "value": "还需复习"},
            {"key": "D", "value": "完全没懂"}
        ],
        "image": None,
        "expected": None
    })

    # ──────── 8. 填空题（单空） ────────
    slide_img = make_slide_image("高等数学 A（下）", [
        "## 第九章 定积分",
        "---",
        "计算定积分：",
        "",
        "  ∫(0→1) 2x dx = ____",
        "",
        "请输入最终数值结果",
    ])
    problems.append({
        "name": "【高数】填空题 — 定积分",
        "problemType": 3,
        "body": "<p>计算定积分：∫(0→1) 2x dx = ____</p>",
        "options": [],
        "image": slide_img,
        "expected": ["1"]
    })

    # ──────── 9. 填空题（多空） ────────
    problems.append({
        "name": "【英语】填空题 — 多空",
        "problemType": 3,
        "body": "<p>Fill in the blanks:</p><p>1. She ____ (go) to school every day.</p><p>2. They ____ (be) very happy yesterday.</p>",
        "options": [],
        "image": None,
        "expected": ["goes", "were"]
    })

    # ──────── 10. 简答题 ────────
    slide_img = make_slide_image("思想道德与法治", [
        "## 第四章 社会主义核心价值观",
        "---",
        "简答题：",
        "",
        "请简述社会主义核心价值观",
        "三个层面的基本内容。",
        "",
        "(不少于 50 字)",
    ])
    problems.append({
        "name": "【思政】简答题 — 核心价值观",
        "problemType": 4,
        "body": "<p>请简述社会主义核心价值观三个层面的基本内容。</p>",
        "options": [],
        "image": slide_img,
        "expected": None
    })

    return problems


# ==================== 格式处理与验证 ====================

def format_result_for_submit(problem_type, ai_answers):
    """模拟 ykt_ws_engine.py submit_answer 中的 result 处理逻辑"""
    if int(problem_type) == 4:
        if isinstance(ai_answers, list):
            content_str = "\n".join(str(item) for item in ai_answers)
        else:
            content_str = str(ai_answers or "")
        return {"content": content_str, "pics": [], "videos": []}

    result = ai_answers
    if int(problem_type) == 1 and isinstance(result, list):
        result = sorted(result, key=lambda x: str(x))
    return result


def validate(problem, ai_answers, formatted):
    """验证 AI 返回结果的格式和内容"""
    errors = []
    ptype = problem["problemType"]

    if not ai_answers:
        errors.append("❌ AI 未返回任何答案")
        return errors

    # 类型检查
    if ptype in (0, 1, 2, 3):
        if not isinstance(ai_answers, list):
            errors.append(f"❌ 期望 list，得到 {type(ai_answers).__name__}")
            return errors
        if not all(isinstance(x, str) for x in ai_answers):
            errors.append(f"❌ 数组元素应全为字符串: {ai_answers}")

    # 单选只能有一个
    if ptype == 0 and isinstance(ai_answers, list) and len(ai_answers) != 1:
        errors.append(f"❌ 单选应返回 1 个答案，实际 {len(ai_answers)}: {ai_answers}")

    # 选择/投票 key 合法性
    if ptype in (0, 1, 2) and isinstance(ai_answers, list):
        valid_keys = {opt["key"] for opt in problem.get("options", [])}
        for ans in ai_answers:
            if ans not in valid_keys:
                errors.append(f"❌ '{ans}' 不在合法选项 {valid_keys} 中")

    # 多选排序检查
    if problem.get("validate_sorted") and isinstance(formatted, list):
        if formatted != sorted(formatted):
            errors.append(f"❌ 多选未按字母排序: {formatted}")

    # 简答题对象格式
    if ptype == 4:
        if not isinstance(formatted, dict):
            errors.append(f"❌ 简答 result 应为 dict")
        elif not formatted.get("content", "").strip():
            errors.append("❌ 简答 content 为空")
        elif "pics" not in formatted or "videos" not in formatted:
            errors.append("❌ 简答缺 pics/videos 字段")

    return errors


# ==================== 主测试流程 ====================

def run_tests():
    type_names = {0: "单选题", 1: "多选题", 2: "投票题", 3: "填空题", 4: "简答题"}
    problems = build_test_problems()
    total = len(problems)
    format_pass = 0
    content_pass = 0
    results = []

    print()
    print("=" * 72)
    print("  🧪 雨课堂 AI 答题 — 真实场景端到端测试")
    print("  📦 含课件截图多模态测试 | Gemini 3.5 Flash")
    print("=" * 72)
    print()

    for idx, p in enumerate(problems):
        type_str = type_names.get(p["problemType"], "?")
        has_img = "📸" if p.get("image") else "📝"
        print(f"━━━ [{idx+1}/{total}] {has_img} {p['name']} ━━━")

        body_preview = (p["body"] or "(无题干 — 纯图片识别)").replace("<p>", "").replace("</p>", "")[:70]
        print(f"  题型: {type_str}  |  图片: {'有 (%d KB)' % (len(p['image'])//1024) if p.get('image') else '无'}")
        print(f"  题干: {body_preview}")
        if p["options"]:
            opts_str = " | ".join(f"{o['key']}.{o['value'][:12]}" for o in p["options"])
            print(f"  选项: {opts_str}")
        if p.get("note"):
            print(f"  📌 {p['note']}")

        # 调用 AI
        t0 = time.time()
        try:
            ai_answers = solve_yuketang_problem(
                problem_type=p["problemType"],
                body_html=p["body"],
                options=p["options"],
                image_bytes=p.get("image")
            )
        except Exception as e:
            ai_answers = []
            print(f"  💥 异常: {e}")
        elapsed = round(time.time() - t0, 2)

        # 格式转换（模拟 submit_answer）
        formatted = format_result_for_submit(p["problemType"], ai_answers)

        # 验证
        errors = validate(p, ai_answers, formatted)
        fmt_ok = len(errors) == 0

        # 答案正确性
        expected = p.get("expected")
        if expected and isinstance(ai_answers, list):
            content_ok = sorted(ai_answers) == sorted(expected)
        elif expected is None:
            content_ok = True  # 主观/投票题
        else:
            content_ok = False

        if fmt_ok:
            format_pass += 1
        if content_ok:
            content_pass += 1

        # 打印结果
        print(f"  ⏱️  {elapsed}s  |  AI 返回: {json.dumps(ai_answers, ensure_ascii=False)}")
        if p["problemType"] == 4:
            content_preview = formatted.get("content", "")[:60] if isinstance(formatted, dict) else str(formatted)[:60]
            print(f"  📤 提交格式: {{content: \"{content_preview}...\", pics:[], videos:[]}}")
        else:
            print(f"  📤 提交格式: {json.dumps(formatted, ensure_ascii=False)}")

        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print(f"  ✅ 格式正确", end="")
            if expected:
                if content_ok:
                    print(f"  |  🎯 答案正确 (期望 {expected})")
                else:
                    print(f"  |  ⚠️  答案: {ai_answers}, 期望: {expected}")
            else:
                print(f"  |  ℹ️  主观/投票题")
        print()

        results.append({
            "idx": idx + 1,
            "name": p["name"][:22],
            "type": type_str,
            "has_img": bool(p.get("image")),
            "elapsed": elapsed,
            "answer": ai_answers,
            "fmt_ok": fmt_ok,
            "content_ok": content_ok,
            "errors": errors
        })

    # ==================== 汇总报告 ====================
    print("=" * 72)
    print("  📊 测试汇总报告")
    print("=" * 72)
    print()
    print(f"  {'#':>2}  {'题型':<6} {'图':>2} {'耗时':>5}  {'格式':>2} {'答案':>2}  {'AI结果':<20}  题目")
    print(f"  {'─'*2}  {'─'*6} {'─'*2} {'─'*5}  {'─'*2} {'─'*2}  {'─'*20}  {'─'*22}")
    for r in results:
        img_mark = "📸" if r["has_img"] else "  "
        fmt_mark = "✅" if r["fmt_ok"] else "❌"
        ans_mark = "✅" if r["content_ok"] else "⚠️"
        ans_str = json.dumps(r["answer"], ensure_ascii=False)[:18] if r["answer"] else "(空)"
        print(f"  {r['idx']:>2}  {r['type']:<6} {img_mark} {r['elapsed']:>4.1f}s  {fmt_mark}  {ans_mark}  {ans_str:<20}  {r['name']}")

    print()
    print(f"  格式验证: {format_pass}/{total} 通过  {'✅ 全部通过' if format_pass == total else '⚠️ 存在格式问题'}")
    print(f"  答案正确: {content_pass}/{total} 正确")
    img_count = sum(1 for r in results if r["has_img"])
    print(f"  多模态题: {img_count}/{total} 道题附带课件截图")
    print()

    if format_pass == total:
        print("  🎉 所有题目格式验证通过！答题提交管线安全可用。")
    else:
        failed = [r for r in results if not r["fmt_ok"]]
        print(f"  ⚠️  以下题目格式异常：")
        for r in failed:
            print(f"     #{r['idx']} {r['name']}: {r['errors']}")
    print()


if __name__ == "__main__":
    run_tests()
