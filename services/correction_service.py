"""
AI 纠错服务。

负责：
1. 调用大模型检查用户英文回答；
2. 输出结构化纠错结果；
3. 提供历史纠错 Markdown 展示；
4. AI 调用失败时提供兜底纠错，保证 Demo 不崩。
"""

from services.llm_service import call_llm_json


def _fallback_correction(sentence):
    """AI 调用失败时的兜底纠错。"""

    text = sentence.strip()

    if "very like" in text.lower():
        return {
            "original": sentence,
            "corrected": text.replace("very like", "really like"),
            "error_type": "expression",
            "explanation": "英文里 very 通常修饰形容词，不能直接修饰 like，建议用 really like。",
            "better_expression": "I am very interested in this topic.",
            "severity": "medium",
            "has_error": True
        }

    return {
        "original": sentence,
        "corrected": sentence,
        "error_type": "none",
        "explanation": "没有发现明显语法错误，可以继续练习更自然、更具体的表达。",
        "better_expression": sentence,
        "severity": "low",
        "has_error": False
    }


def _normalize_correction(data, sentence):
    """统一 AI 返回格式，避免字段缺失导致页面报错。"""

    if not isinstance(data, dict):
        return _fallback_correction(sentence)

    has_error = data.get("has_error", True)

    return {
        "original": data.get("original") or sentence,
        "corrected": data.get("corrected") or sentence,
        "error_type": data.get("error_type") or "expression",
        "explanation": data.get("explanation") or "暂无解释。",
        "better_expression": data.get("better_expression") or data.get("corrected") or sentence,
        "severity": data.get("severity") or "medium",
        "has_error": bool(has_error)
    }


def correct_sentence(sentence):
    """
    对用户输入的一句英文进行 AI 纠错。

    返回格式：
    {
        "original": "...",
        "corrected": "...",
        "error_type": "grammar/expression/vocabulary/pronunciation/none",
        "explanation": "...",
        "better_expression": "...",
        "severity": "low/medium/high",
        "has_error": true/false
    }
    """

    if not sentence or not sentence.strip():
        return {
            "original": "",
            "corrected": "",
            "error_type": "none",
            "explanation": "用户没有输入内容。",
            "better_expression": "",
            "severity": "low",
            "has_error": False
        }

    messages = [
        {
            "role": "system",
            "content": """
You are an English speaking coach.

Your task is to correct one English sentence from a learner.

Return ONLY valid JSON. Do not use markdown. Do not add extra text.

JSON schema:
{
  "original": "the original user sentence",
  "corrected": "the corrected sentence",
  "error_type": "grammar | expression | vocabulary | word_order | none",
  "explanation": "explain the problem in Chinese, short and clear",
  "better_expression": "a more natural English expression",
  "severity": "low | medium | high",
  "has_error": true
}

Rules:
1. If the sentence has no obvious error, set error_type to "none" and has_error to false.
2. The explanation should be in Chinese because the learner is Chinese.
3. The corrected and better_expression fields must be in English.
4. Be practical and concise.
""".strip()
        },
        {
            "role": "user",
            "content": sentence.strip()
        }
    ]

    try:
        data = call_llm_json(messages, temperature=0.2)
        return _normalize_correction(data, sentence)

    except Exception as error:
        print("AI correction error:", error)
        return _fallback_correction(sentence)


def format_correction_history(corrections):
    """
    把历史纠错记录转成 Markdown，方便 Gradio 页面展示。
    """

    if not corrections:
        return "暂无历史错误记录。"

    error_items = []

    for index, item in enumerate(corrections, start=1):
        if not isinstance(item, dict):
            continue

        has_error = item.get("has_error", True)
        error_type = item.get("error_type", "expression")

        if not has_error or error_type == "none":
            continue

        original = item.get("original", "")
        corrected = item.get("corrected", "")
        better = item.get("better_expression", "")
        explanation = item.get("explanation", "")
        severity = item.get("severity", "medium")

        error_items.append(
            f"""
### {len(error_items) + 1}. {error_type} / {severity}

**原句：**

> {original}

**修改后：**

> {corrected}

**更自然表达：**

> {better}

**说明：**

{explanation}
""".strip()
        )

    if not error_items:
        return "目前没有明显历史错误，继续保持。"

    return "\n\n---\n\n".join(error_items)
