"""
AI 对话教练服务。

这个模块负责：
1. 根据当前练习场景生成 AI 角色提示词
2. 读取用户历史对话
3. 调用外部大模型生成自然追问
4. 在 AI 调用失败时提供兜底回复，保证 Demo 不崩
"""

from services.llm_service import call_llm


def _get_scene_value(scene, key, default=""):
    """
    兼容 dict / 字符串两种场景数据。
    """

    if isinstance(scene, dict):
        return scene.get(key, default)

    return default


def _safe_join(value):
    """
    把 goals / keywords 这类列表转成字符串。
    """

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    if value is None:
        return ""

    return str(value)


def _scene_name(scene):
    if isinstance(scene, dict):
        return scene.get("name") or scene.get("id") or "English Speaking Practice"

    if isinstance(scene, str):
        return scene

    return "English Speaking Practice"


def build_scene_prompt(scene):
    """
    根据场景配置构建系统提示词。
    """

    name = _scene_name(scene)
    ai_role = _get_scene_value(scene, "ai_role", "")
    user_role = _get_scene_value(scene, "user_role", "")
    difficulty = _get_scene_value(scene, "difficulty", "B1-B2")
    goals = _safe_join(_get_scene_value(scene, "goals", []))
    keywords = _safe_join(_get_scene_value(scene, "keywords", []))

    if not ai_role:
        ai_role = _get_scene_value(scene, "role_ai", "English speaking coach")

    if not user_role:
        user_role = _get_scene_value(scene, "role_user", "English learner")

    return f"""
You are EchoCoach, an AI English speaking coach.

Current practice scene:
- Scene: {name}
- Your role: {ai_role}
- User role: {user_role}
- Difficulty level: {difficulty}
- Training goals: {goals}
- Useful keywords: {keywords}

Your job:
1. Continue the conversation naturally in English.
2. Stay in the current role and scene.
3. Ask one specific follow-up question based on the user's latest answer.
4. Keep your reply short, usually 1 to 3 sentences.
5. Do not give long grammar explanations here.
6. Do not switch to Chinese.
7. Do not make the conversation sound like a fixed template.
8. If the user gives a short answer, ask them to explain more.
9. If the user goes off-topic, gently bring them back to the scene.
10. If the user makes grammar mistakes, do not correct them here. Another correction module will handle that.

Output only the AI reply in English.
""".strip()


def normalize_chat_history(chat_history, max_messages=10):
    """
    兼容不同格式的历史对话。

    支持：
    1. [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    2. [["user text", "assistant text"], ...]
    3. [("user text", "assistant text"), ...]
    """

    if not chat_history:
        return []

    messages = []

    for item in chat_history[-max_messages:]:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content", "")

            if role == "ai":
                role = "assistant"

            if role in ["user", "assistant"] and content:
                messages.append(
                    {
                        "role": role,
                        "content": str(content)
                    }
                )

        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            user_text = item[0]
            assistant_text = item[1]

            if user_text:
                messages.append(
                    {
                        "role": "user",
                        "content": str(user_text)
                    }
                )

            if assistant_text:
                messages.append(
                    {
                        "role": "assistant",
                        "content": str(assistant_text)
                    }
                )

    return messages[-max_messages:]


def fallback_reply(scene, chat_history=None):
    """
    大模型调用失败时的兜底回复。
    这样即使 API 临时出错，Demo 也不会直接崩掉。
    """

    name = _scene_name(scene)

    user_turn_count = 0

    if chat_history:
        for item in chat_history:
            if isinstance(item, dict) and item.get("role") == "user":
                user_turn_count += 1
            elif isinstance(item, (list, tuple)) and len(item) >= 1 and item[0]:
                user_turn_count += 1

    questions = [
        f"Let's continue the {name} practice. Could you tell me more?",
        "That is a good start. Could you give me one specific example?",
        "Interesting. What was the biggest challenge in that situation?",
        "How did you handle that problem?",
        "What did you learn from that experience?",
        "Can you explain your answer in a more detailed way?"
    ]

    index = min(user_turn_count, len(questions) - 1)

    return questions[index]


def generate_ai_reply(scene, chat_history=None, user_message=None):
    """
    生成 AI 动态回复。

    scene:
        当前场景配置

    chat_history:
        历史对话

    user_message:
        用户最新输入。如果 app.py 已经把最新输入放进 chat_history，
        这个参数可以不传。
    """

    system_prompt = build_scene_prompt(scene)

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(normalize_chat_history(chat_history))

    if user_message:
        messages.append(
            {
                "role": "user",
                "content": str(user_message)
            }
        )

    try:
        reply = call_llm(messages, temperature=0.7)

        if not reply or not reply.strip():
            return fallback_reply(scene, chat_history)

        return reply.strip()

    except Exception as error:
        print("AI reply error:", error)
        return fallback_reply(scene, chat_history)


def generate_mock_ai_reply(scene, *args, **kwargs):
    """
    保留旧函数名，避免 app.py 暂时不用改。

    兼容这些调用方式：
    1. generate_mock_ai_reply(scene, chat_history)
    2. generate_mock_ai_reply(scene, user_message, chat_history)
    3. generate_mock_ai_reply(scene, chat_history, user_message)
    """

    chat_history = kwargs.get("chat_history")
    user_message = kwargs.get("user_message") or kwargs.get("user_input")

    for arg in args:
        if isinstance(arg, list):
            chat_history = arg
        elif isinstance(arg, str):
            user_message = arg

    return generate_ai_reply(
        scene=scene,
        chat_history=chat_history,
        user_message=user_message
    )


def generate_opening_message(scene):
    """
    生成开场白。
    如果场景配置里有 opening_message，就优先用配置。
    """

    if isinstance(scene, dict):
        opening = scene.get("opening_message")

        if opening:
            return opening

    name = _scene_name(scene)

    return f"Welcome to the {name} practice. Let's begin. Could you introduce yourself first?"


def get_opening_message(scene):
    """
    兼容可能存在的旧函数名。
    """

    return generate_opening_message(scene)
