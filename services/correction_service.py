"""
英文纠错模块。

这个文件负责检查用户输入的英文回答，并给出轻量级纠错建议。

当前版本说明：
1. 先不接真实大模型；
2. 使用规则匹配实现基础语法和表达纠错；
3. 返回结构化结果，方便页面展示；
4. 后续可以替换为 LLM 纠错服务。
"""


def build_no_input_feedback():
    """
    当用户没有输入内容时，返回提示。
    """

    return {
        "原句": "",
        "修改后": "",
        "错误类型": "无输入",
        "问题说明": "没有检测到英文输入。",
        "更自然表达": "",
        "严重程度": "低"
    }


def build_no_error_feedback(user_text: str):
    """
    当没有发现明显错误时，返回鼓励和表达优化建议。
    """

    return {
        "原句": user_text,
        "修改后": user_text,
        "错误类型": "未发现明显错误",
        "问题说明": "当前轻量版规则没有发现明显语法错误。",
        "更自然表达": "You can add one specific example to make your answer more natural.",
        "严重程度": "低"
    }


def correct_common_expression(user_text: str, lower_text: str):
    """
    检查常见表达错误。

    当前主要覆盖一些初学者高频错误。
    """

    if "i very like" in lower_text:
        corrected = user_text.replace("I very like", "I really like")
        corrected = corrected.replace("i very like", "I really like")

        return {
            "原句": user_text,
            "修改后": corrected,
            "错误类型": "表达错误",
            "问题说明": "英文中 very 通常修饰形容词，不直接修饰 like 这样的动词。这里更自然的说法是 really like。",
            "更自然表达": "I am very interested in this opportunity.",
            "严重程度": "中"
        }

    if "more better" in lower_text:
        corrected = user_text.replace("more better", "better")
        corrected = corrected.replace("More better", "Better")

        return {
            "原句": user_text,
            "修改后": corrected,
            "错误类型": "语法错误",
            "问题说明": "better 本身已经是比较级，不需要再加 more。",
            "更自然表达": corrected,
            "严重程度": "中"
        }

    return None


def correct_subject_verb_agreement(user_text: str, lower_text: str):
    """
    检查简单的主谓一致错误。
    """

    if "i has" in lower_text:
        corrected = user_text.replace("I has", "I have")
        corrected = corrected.replace("i has", "I have")

        return {
            "原句": user_text,
            "修改后": corrected,
            "错误类型": "语法错误",
            "问题说明": "第一人称 I 后面应该使用 have，而不是 has。",
            "更自然表达": corrected,
            "严重程度": "高"
        }

    if "he have" in lower_text:
        corrected = user_text.replace("he have", "he has")
        corrected = corrected.replace("He have", "He has")

        return {
            "原句": user_text,
            "修改后": corrected,
            "错误类型": "语法错误",
            "问题说明": "第三人称单数 he 后面应该使用 has。",
            "更自然表达": corrected,
            "严重程度": "中"
        }

    if "she have" in lower_text:
        corrected = user_text.replace("she have", "she has")
        corrected = corrected.replace("She have", "She has")

        return {
            "原句": user_text,
            "修改后": corrected,
            "错误类型": "语法错误",
            "问题说明": "第三人称单数 she 后面应该使用 has。",
            "更自然表达": corrected,
            "严重程度": "中"
        }

    return None


def check_answer_completeness(user_text: str):
    """
    检查回答是否过短。

    口语训练中，太短的回答不利于练习表达能力。
    """

    word_count = len(user_text.split())

    if word_count < 5:
        return {
            "原句": user_text,
            "修改后": user_text,
            "错误类型": "表达不完整",
            "问题说明": "你的回答可以理解，但内容比较短。建议使用完整句子，并补充一个具体例子。",
            "更自然表达": "Try to answer with a complete sentence and one specific example.",
            "严重程度": "低"
        }

    return None


def correct_sentence(user_text: str):
    """
    对用户输入的英文句子进行轻量纠错。

    返回结构化字典，便于 Gradio 页面展示。
    """

    if not user_text or not user_text.strip():
        return build_no_input_feedback()

    cleaned_text = user_text.strip()
    lower_text = cleaned_text.lower()

    # 先检查常见表达错误。
    expression_feedback = correct_common_expression(cleaned_text, lower_text)
    if expression_feedback:
        return expression_feedback

    # 再检查简单主谓一致错误。
    grammar_feedback = correct_subject_verb_agreement(cleaned_text, lower_text)
    if grammar_feedback:
        return grammar_feedback

    # 再检查回答是否过短。
    completeness_feedback = check_answer_completeness(cleaned_text)
    if completeness_feedback:
        return completeness_feedback

    # 如果没有命中规则，返回无明显错误。
    return build_no_error_feedback(cleaned_text)
