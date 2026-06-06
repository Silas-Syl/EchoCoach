"""
课后总结报告模块。

根据本次练习的聊天记录、纠错记录和评分结果，
生成结构化课后总结报告。
"""

from typing import Dict, List

from services.scoring_service import generate_scores


Message = Dict[str, str]
Correction = Dict[str, str]


def get_user_messages(chat_history: List[Message]) -> List[str]:
    """提取用户回答内容。"""

    if not chat_history:
        return []

    return [
        message.get("content", "")
        for message in chat_history
        if message.get("role") == "user"
    ]


def collect_typical_errors(corrections: List[Correction]) -> List[Dict[str, str]]:
    """整理典型错误。"""

    if not corrections:
        return [
            {
                "原句": "暂无",
                "修改建议": "暂无",
                "说明": "本次练习还没有产生纠错记录。"
            }
        ]

    typical_errors = []

    for correction in corrections:
        error_type = correction.get("错误类型", "")

        if error_type in ["未发现明显错误", "无输入"]:
            continue

        typical_errors.append(
            {
                "原句": correction.get("原句", ""),
                "修改建议": correction.get("修改后", ""),
                "说明": correction.get("问题说明", "")
            }
        )

    if not typical_errors:
        return [
            {
                "原句": "未发现明显高频错误",
                "修改建议": "继续尝试更长、更自然的英文表达。",
                "说明": "本次练习没有发现明显语法或表达问题。"
            }
        ]

    return typical_errors


def build_strengths(scores: Dict) -> List[str]:
    """根据评分生成优点总结。"""

    score_result = scores.get("评分结果", {})
    strengths = []

    if score_result.get("互动完成度", 0) >= 70:
        strengths.append("你能够持续参与对话，互动完成度较好。")

    if score_result.get("场景完成度", 0) >= 70:
        strengths.append("你的回答和当前练习场景关联度较高。")

    if score_result.get("语法准确度", 0) >= 80:
        strengths.append("本次练习中的语法错误较少。")

    if not strengths:
        strengths.append("你已经完成了基础对话练习，可以继续增加回答长度和表达细节。")

    return strengths


def build_weaknesses(scores: Dict) -> List[str]:
    """根据评分生成待改进问题。"""

    score_result = scores.get("评分结果", {})
    weaknesses = []

    if score_result.get("流利度", 100) < 75:
        weaknesses.append("部分回答偏短，可以尝试用更完整的句子表达。")

    if score_result.get("表达自然度", 100) < 80:
        weaknesses.append("部分表达不够自然，可以积累更多地道英文表达。")

    if score_result.get("场景完成度", 100) < 75:
        weaknesses.append("回答中和场景目标相关的关键词还不够多。")

    if not weaknesses:
        weaknesses.append("整体表现比较稳定，下一步可以提升回答的丰富度和细节。")

    return weaknesses


def build_practice_suggestions(scene: Dict, scores: Dict) -> List[str]:
    """生成复练建议。"""

    scene_name = scene.get("name", "")
    suggestions = [
        f"继续练习 {scene_name} 场景，尝试完成更多轮对话。",
        "回答时尽量使用完整句子，而不是只回答几个单词。",
        "复习本次典型错误，并尝试重新说出修改后的句子。"
    ]

    if scene.get("id") == "job_interview":
        suggestions.append("面试场景中可以尝试使用 STAR 方法描述项目经历。")

    return suggestions


def generate_report(scene: Dict, chat_history: List[Message], corrections: List[Correction]) -> Dict:
    """生成完整课后总结报告。"""

    user_messages = get_user_messages(chat_history)
    scores = generate_scores(scene, chat_history, corrections)

    return {
        "练习概览": {
            "练习场景": scene.get("name", ""),
            "用户回答轮数": len(user_messages),
            "纠错记录数量": len(corrections) if corrections else 0
        },
        "能力评分": scores,
        "优点总结": build_strengths(scores),
        "待改进问题": build_weaknesses(scores),
        "典型错误": collect_typical_errors(corrections),
        "复练建议": build_practice_suggestions(scene, scores),
        "报告说明": "当前为轻量版课后报告，主要基于用户回答、纠错记录和轻量评分生成。后续可接入大模型生成更自然的个性化总结。"
    }
