"""
口语评分模块。

根据用户真实聊天记录和历史纠错记录，生成轻量版动态口语能力评分。

特点：
1. 不调用 AI，保证每轮发送速度；
2. 根据用户输入长度、错误数量、错误严重程度、互动轮次、场景关键词命中动态评分；
3. 兼容新版纠错字段：error_type / severity / has_error；
4. 兼容旧版中文字段：错误类型 / 严重程度。
"""

import re
from typing import Dict, List, Any


Message = Dict[str, str]
Correction = Dict[str, Any]


def clamp(value: int, min_value: int = 40, max_value: int = 100) -> int:
    """限制分数范围。"""
    return max(min_value, min(max_value, int(value)))


def get_user_messages(chat_history: List[Message]) -> List[str]:
    """从聊天记录中提取用户回答。"""

    if not chat_history:
        return []

    user_messages = []

    for message in chat_history:
        if not isinstance(message, dict):
            continue

        if message.get("role") == "user":
            content = message.get("content", "")
            if content:
                user_messages.append(str(content))

    return user_messages


def count_words(text: str) -> int:
    """统计英文单词数量。"""

    if not text:
        return 0

    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    return len(words)


def normalize_error_type(correction: Correction) -> str:
    """
    统一错误类型字段。

    新字段：
    - error_type: grammar / expression / vocabulary / word_order / none

    旧字段：
    - 错误类型: 语法错误 / 表达错误 / 表达不完整 / 未发现明显错误
    """

    error_type = correction.get("error_type")

    if error_type:
        return str(error_type).lower()

    old_type = correction.get("错误类型", "")

    mapping = {
        "语法错误": "grammar",
        "表达错误": "expression",
        "表达不完整": "expression",
        "词汇错误": "vocabulary",
        "词序错误": "word_order",
        "未发现明显错误": "none",
        "无输入": "none",
    }

    return mapping.get(old_type, "none")


def normalize_severity(correction: Correction) -> str:
    """
    统一严重程度字段。

    新字段：
    - severity: low / medium / high

    旧字段：
    - 严重程度: 低 / 中 / 高
    """

    severity = correction.get("severity")

    if severity:
        return str(severity).lower()

    old_severity = correction.get("严重程度", "低")

    mapping = {
        "低": "low",
        "中": "medium",
        "高": "high",
    }

    return mapping.get(old_severity, "low")


def has_real_error(correction: Correction) -> bool:
    """判断一条纠错记录是否是真实错误。"""

    if not isinstance(correction, dict):
        return False

    if correction.get("has_error") is False:
        return False

    error_type = normalize_error_type(correction)

    if error_type in ["none", "no_error", ""]:
        return False

    return True


def severity_penalty(severity: str) -> int:
    """根据严重程度返回扣分。"""

    if severity == "high":
        return 15

    if severity == "medium":
        return 8

    return 3


def calculate_fluency_score(chat_history: List[Message]) -> int:
    """
    计算流利度。

    依据：
    - 平均回答长度；
    - 是否能展开说明；
    - 回答太短会扣分。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return 50

    word_counts = [count_words(message) for message in user_messages]
    average_words = sum(word_counts) / len(word_counts)

    if average_words >= 18:
        score = 92
    elif average_words >= 13:
        score = 85
    elif average_words >= 8:
        score = 76
    elif average_words >= 4:
        score = 66
    else:
        score = 58

    very_short_count = sum(1 for count in word_counts if count <= 3)

    if very_short_count >= 2:
        score -= 8

    return clamp(score)


def calculate_grammar_score(corrections: List[Correction]) -> int:
    """
    计算语法准确度。

    依据：
    - grammar 和 word_order 错误主要影响语法准确度；
    - expression / vocabulary 轻微影响语法准确度；
    - high / medium / low 扣分不同。
    """

    if not corrections:
        return 85

    penalty = 0

    for correction in corrections:
        if not has_real_error(correction):
            continue

        error_type = normalize_error_type(correction)
        severity = normalize_severity(correction)
        base_penalty = severity_penalty(severity)

        if error_type in ["grammar", "word_order"]:
            penalty += base_penalty
        elif error_type in ["expression", "vocabulary"]:
            penalty += max(2, base_penalty // 2)

    return clamp(100 - penalty)


def calculate_expression_score(corrections: List[Correction]) -> int:
    """
    计算表达自然度。

    依据：
    - expression / vocabulary 错误主要影响表达自然度；
    - grammar / word_order 也会轻微影响表达自然度。
    """

    if not corrections:
        return 82

    penalty = 0

    for correction in corrections:
        if not has_real_error(correction):
            continue

        error_type = normalize_error_type(correction)
        severity = normalize_severity(correction)
        base_penalty = severity_penalty(severity)

        if error_type in ["expression", "vocabulary"]:
            penalty += base_penalty
        elif error_type in ["grammar", "word_order"]:
            penalty += max(2, base_penalty // 2)

    return clamp(100 - penalty)


def calculate_interaction_score(chat_history: List[Message]) -> int:
    """
    计算互动能力。

    依据：
    - 用户回答轮数；
    - 回答是否有一定长度；
    - 是否持续参与对话。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return 50

    user_turn_count = len(user_messages)
    word_counts = [count_words(message) for message in user_messages]

    score = 55 + user_turn_count * 8

    detailed_turns = sum(1 for count in word_counts if count >= 8)
    score += detailed_turns * 4

    short_turns = sum(1 for count in word_counts if count <= 3)
    score -= short_turns * 5

    return clamp(score)


def build_scene_terms(scene: Dict) -> List[str]:
    """
    构建场景关键词。

    来源：
    1. keywords；
    2. goals 中长度较长的英文词。
    """

    if not isinstance(scene, dict):
        return []

    terms = []

    for keyword in scene.get("keywords", []):
        keyword = str(keyword).lower().strip()
        if keyword:
            terms.append(keyword)

    for goal in scene.get("goals", []):
        words = re.findall(r"[A-Za-z]+", str(goal).lower())

        for word in words:
            if len(word) >= 4:
                terms.append(word)

    return sorted(set(terms))


def calculate_scenario_completion_score(scene: Dict, chat_history: List[Message]) -> int:
    """
    计算场景完成度。

    依据：
    - 用户回答是否命中当前场景关键词；
    - 是否覆盖场景目标中的核心词。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return 50

    scene_terms = build_scene_terms(scene)

    if not scene_terms:
        return 70

    user_text = " ".join(user_messages).lower()

    matched_terms = []

    for term in scene_terms:
        if term in user_text:
            matched_terms.append(term)

    matched_ratio = len(matched_terms) / len(scene_terms)

    score = 55 + int(matched_ratio * 45)

    return clamp(score)


def calculate_overall_score(scores: Dict[str, int]) -> int:
    """
    计算总分。

    权重：
    - 流利度 25%
    - 语法准确度 25%
    - 表达自然度 20%
    - 互动能力 15%
    - 场景完成度 15%
    """

    overall = (
        scores["流利度"] * 0.25
        + scores["语法准确度"] * 0.25
        + scores["表达自然度"] * 0.20
        + scores["互动能力"] * 0.15
        + scores["场景完成度"] * 0.15
    )

    return round(overall)


def build_feedback(scores: Dict[str, int], corrections: List[Correction]) -> str:
    """生成简短中文反馈。"""

    overall = scores["总分"]

    real_errors = [
        item for item in corrections or []
        if isinstance(item, dict) and has_real_error(item)
    ]

    if overall >= 85:
        level_comment = "你的整体表现不错，回答比较完整，也能较好地贴合当前场景。"
    elif overall >= 70:
        level_comment = "你的回答可以完成基本交流，但还需要增加细节，并减少语法或表达问题。"
    else:
        level_comment = "你已经开始尝试表达，但回答偏短，建议用更完整的句子展开说明。"

    if real_errors:
        error_comment = f"本次目前累计发现 {len(real_errors)} 个明显问题，建议优先复习历史错误记录中的典型表达。"
    else:
        error_comment = "目前没有发现明显错误，可以继续挑战更自然、更具体的表达。"

    lowest_dimension = min(
        ["流利度", "语法准确度", "表达自然度", "互动能力", "场景完成度"],
        key=lambda key: scores[key]
    )

    improve_comment = f"当前最需要提升的维度是：{lowest_dimension}。"

    return f"{level_comment}{error_comment}{improve_comment}"


def generate_scores(scene: Dict, chat_history: List[Message], corrections: List[Correction]) -> Dict:
    """
    生成完整评分结果。

    返回给 Gradio JSON 组件展示，同时供课后报告使用。
    """

    if corrections is None:
        corrections = []

    scores = {
        "流利度": calculate_fluency_score(chat_history),
        "语法准确度": calculate_grammar_score(corrections),
        "表达自然度": calculate_expression_score(corrections),
        "互动能力": calculate_interaction_score(chat_history),
        "场景完成度": calculate_scenario_completion_score(scene, chat_history),
    }

    scores["总分"] = calculate_overall_score(scores)

    return {
        "当前场景": scene.get("name", "") if isinstance(scene, dict) else "",
        "评分说明": "当前为轻量版动态评分，主要基于用户回答长度、历史纠错、互动轮次和场景关键词命中情况。",
        "评分结果": scores,
        "反馈建议": build_feedback(scores, corrections),
    }
