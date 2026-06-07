"""
课后总结报告模块。

负责：
1. 根据完整对话记录、历史纠错和评分，调用 AI 生成个性化课后总结；
2. AI 调用失败时提供规则兜底报告，保证 Demo 不崩。
"""

from services.llm_service import call_llm


def _format_scores_text(scores):
    """把评分字典格式化成文本，方便传给 AI。"""

    if not scores or "评分结果" not in scores:
        return "暂无评分数据。"

    results = scores["评分结果"]
    lines = []

    for key, value in results.items():
        if key != "总分":
            lines.append(f"- {key}：{value} 分")

    return "\n".join(lines)


def _format_scores_markdown(scores):
    """把评分字典格式化成 Markdown 表格，用于兜底报告。"""

    if not scores or "评分结果" not in scores:
        return "暂无评分数据。"

    results = scores["评分结果"]
    lines = ["| 维度 | 分数 |", "|---|---|"]

    for key, value in results.items():
        if key != "总分":
            lines.append(f"| {key} | {value} |")

    return "\n".join(lines)


def _fallback_report(scene, chat_history, corrections, scores):
    """
    AI 调用失败时的规则兜底报告。
    保证点击"结束练习"时页面一定能显示内容。
    """

    name = scene.get("name", "English Practice") if isinstance(scene, dict) else str(scene)

    user_turns = [m for m in (chat_history or []) if m.get("role") == "user"]
    turn_count = len(user_turns)

    overall = "N/A"
    if scores and "评分结果" in scores:
        overall = scores["评分结果"].get("总分", "N/A")

    error_items = []
    for correction in (corrections or []):
        if not isinstance(correction, dict):
            continue
        if correction.get("has_error") and correction.get("error_type") != "none":
            original = correction.get("original", "")
            corrected = correction.get("corrected", "")
            explanation = correction.get("explanation", "")
            if original:
                error_items.append(f"- **原句：** {original}\n  **修改：** {corrected}\n  **说明：** {explanation}")

    errors_section = "\n\n".join(error_items) if error_items else "本次练习未发现明显错误，继续保持！"

    scores_md = _format_scores_markdown(scores)

    return f"""## 本次练习总结

**练习场景：** {name}
**完成轮数：** {turn_count} 轮对话
**综合评分：** {overall} / 100

---

### 分项评分

{scores_md}

---

### 典型错误记录

{errors_section}

---

### 下次练习建议

1. 尝试用更完整的句子来回答问题，包含主谓宾和具体细节。
2. 注意动词后的介词搭配和名词单复数。
3. 练习用 STAR 结构（Situation / Task / Action / Result）描述经历。
4. 多使用连接词（however, therefore, for example）让表达更流畅。

---

*本次总结由规则引擎生成（AI 模块暂时不可用）。*
"""


def generate_report(scene, chat_history, corrections, scores):
    """
    生成个性化课后总结报告。

    参数：
        scene: 当前场景配置字典
        chat_history: 完整对话记录
        corrections: 历史纠错记录
        scores: 当前评分字典

    返回：
        Markdown 格式的总结报告字符串
    """

    if not chat_history:
        return "本次练习没有对话记录，无法生成总结。"

    name = scene.get("name", "English Practice") if isinstance(scene, dict) else str(scene)
    goals = scene.get("goals", []) if isinstance(scene, dict) else []

    user_messages = [m["content"] for m in chat_history if m.get("role") == "user"]
    turn_count = len(user_messages)

    # 最多取最近 6 句用户回答作为样本
    user_samples = "\n".join(f"- {msg}" for msg in user_messages[-6:])

    # 整理错误列表
    error_lines = []
    for correction in (corrections or []):
        if not isinstance(correction, dict):
            continue
        if correction.get("has_error") and correction.get("error_type") != "none":
            original = correction.get("original", "")
            corrected = correction.get("corrected", "")
            better = correction.get("better_expression", "")
            explanation = correction.get("explanation", "")
            error_lines.append(
                f'原句: "{original}" → 修改: "{corrected}" | 更自然: "{better}" | 说明: {explanation}'
            )

    errors_text = "\n".join(error_lines) if error_lines else "未发现明显错误。"
    goals_text = "\n".join(f"- {g}" for g in goals) if goals else "无"
    scores_text = _format_scores_text(scores)
    overall = scores.get("评分结果", {}).get("总分", "N/A") if scores else "N/A"

    messages = [
        {
            "role": "system",
            "content": """You are an English speaking coach. Generate a personalized practice report in Chinese.

The report must be in Markdown format and include:
1. 本次练习概览（场景、轮数、总分）
2. 分项评分展示
3. 表现亮点（genuine and specific）
4. 主要问题（honest but encouraging）
5. 典型错误与更自然表达（with specific examples）
6. 下次练习建议（actionable, specific to this scene）

Write entirely in Chinese. Use Markdown headers (##, ###) and formatting.
Be warm, encouraging, and specific. Avoid generic advice."""
        },
        {
            "role": "user",
            "content": f"""请根据以下练习数据生成个性化课后总结报告：

练习场景：{name}
完成对话轮数：{turn_count}
场景训练目标：
{goals_text}

用户回答样本（最近 6 句）：
{user_samples}

历史错误记录：
{errors_text}

能力评分结果：
总分：{overall} / 100
{scores_text}

请生成完整、个性化的课后总结报告。"""
        }
    ]

    try:
        report = call_llm(messages, temperature=0.5)

        if report and report.strip():
            return report.strip()

        return _fallback_report(scene, chat_history, corrections, scores)

    except Exception as error:
        print("Report generation error:", error)
        return _fallback_report(scene, chat_history, corrections, scores)

