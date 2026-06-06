"""
口语评分模块。

这个文件负责根据用户的聊天记录和纠错记录，生成轻量版口语能力评分。

当前版本说明：
1. 不做专业音素级发音评分；
2. 先基于文本长度、纠错数量、场景关键词命中等信息进行轻量评估；
3. 评分结果用于页面展示和后续课后报告；
4. 后续可以接入更专业的发音评测模型。
"""

from typing import Dict, List


Message = Dict[str, str]
Correction = Dict[str, str]


def get_user_messages(chat_history: List[Message]) -> List[str]:
    """
    从聊天记录中提取所有用户回答。

    只统计 role 为 user 的消息，AI 的回复不参与用户能力评分。
    """

    if not chat_history:
        return []

    return [
        message.get("content", "")
        for message in chat_history
        if message.get("role") == "user"
    ]


def count_words(text: str) -> int:
    """
    统计英文单词数量。

    当前用空格切分，适合 MVP 阶段。
    后续如果要更准确，可以使用 NLP 分词工具。
    """

    if not text:
        return 0

    return len(text.strip().split())


def calculate_fluency_score(chat_history: List[Message]) -> int:
    """
    计算流利度分数。

    当前轻量版逻辑：
    - 用户平均回答越完整，流利度越高；
    - 回答太短说明表达展开不足。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return 50

    total_words = sum(count_words(message) for message in user_messages)
    average_words = total_words / len(user_messages)

    if average_words >= 15:
        return 90

    if average_words >= 10:
        return 80

    if average_words >= 6:
        return 70

    return 60


def get_severity_penalty(severity: str) -> int:
    """
    根据错误严重程度返回扣分值。
    """

    if severity == "高":
        return 15

    if severity == "中":
        return 8

    return 3


def calculate_grammar_score(corrections: List[Correction]) -> int:
    """
    计算语法准确度分数。

    当前轻量版逻辑：
    - 根据纠错记录中的错误类型和严重程度扣分；
    - 未发现明显错误时不扣分。
    """

    if not corrections:
        return 85

    penalty = 0

    for correction in corrections:
        error_type = correction.get("错误类型", "")
        severity = correction.get("严重程度", "低")

        if error_type in ["未发现明显错误", "无输入"]:
            continue

        if error_type == "语法错误":
            penalty += get_severity_penalty(severity)

    return max(40, 100 - penalty)


def calculate_expression_score(corrections: List[Correction]) -> int:
    """
    计算表达自然度分数。

    当前轻量版逻辑：
    - 表达错误、表达不完整会影响表达自然度；
    - 语法错误主要影响语法分，不在这里重复重扣。
    """

    if not corrections:
        return 80

    penalty = 0

    for correction in corrections:
        error_type = correction.get("错误类型", "")

        if error_type == "表达错误":
            penalty += 10

        if error_type == "表达不完整":
            penalty += 8

    return max(45, 100 - penalty)


def calculate_interaction_score(chat_history: List[Message]) -> int:
    """
    计算互动完成度分数。

    当前轻量版逻辑：
    - 用户参与轮次越多，互动完成度越高；
    - 最高不超过 100 分。
    """

    user_turn_count = len(get_user_messages(chat_history))

    return min(100, 50 + user_turn_count * 10)


def build_scene_terms(scene: Dict) -> List[str]:
    """
    构建场景关键词列表。

    关键词来源：
    1. scenes.yaml 中的 keywords；
    2. scenes.yaml 中 goals 里的重要单词。
    """

    terms = []

    for keyword in scene.get("keywords", []):
        terms.append(keyword.lower())

    for goal in scene.get("goals", []):
        for word in goal.lower().replace("-", " ").split():
            if len(word) >= 4:
                terms.append(word)

    return list(set(terms))


def calculate_scenario_completion_score(scene: Dict, chat_history: List[Message]) -> int:
    """
    计算场景完成度分数。

    当前轻量版逻辑：
    - 如果用户回答中命中了更多场景关键词，说明更贴合当前场景；
    - 基础分为 50，最多加到 100。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return 50

    user_text = " ".join(user_messages).lower()
    scene_terms = build_scene_terms(scene)

    if not scene_terms:
        return 70

    matched_count = 0

    for term in scene_terms:
        if term in user_text:
            matched_count += 1

    matched_ratio = matched_count / len(scene_terms)

    return min(100, 50 + int(matched_ratio * 50))


def calculate_overall_score(scores: Dict[str, int]) -> int:
    """
    计算总分。

    权重设计：
    - 流利度：25%
    - 语法准确度：25%
    - 表达自然度：20%
    - 互动完成度：15%
    - 场景完成度：15%
    """

    overall = (
        scores["流利度"] * 0.25
        + scores["语法准确度"] * 0.25
        + scores["表达自然度"] * 0.20
        + scores["互动完成度"] * 0.15
        + scores["场景完成度"] * 0.15
    )

    return round(overall)


def generate_scores(scene: Dict, chat_history: List[Message], corrections: List[Correction]) -> Dict:
    """
    生成完整评分结果。

    返回字典格式，方便 Gradio JSON 组件展示。
    """

    scores = {
        "流利度": calculate_fluency_score(chat_history),
        "语法准确度": calculate_grammar_score(corrections),
        "表达自然度": calculate_expression_score(corrections),
        "互动完成度": calculate_interaction_score(chat_history),
        "场景完成度": calculate_scenario_completion_score(scene, chat_history),
    }

    scores["总分"] = calculate_overall_score(scores)

    return {
        "当前场景": scene.get("name", ""),
        "评分说明": "当前为轻量版评分，主要基于文本长度、纠错记录、互动轮次和场景关键词命中情况。",
        "评分结果": scores,
    }
