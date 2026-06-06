"""
AI 教练回复模块。

这个文件负责根据当前练习场景和用户回答，生成下一句 AI 追问。

当前版本说明：
1. 先不接真实大模型；
2. 使用规则判断模拟 AI 回复；
3. 会根据用户回答内容做简单判断；
4. 后续可以把这里替换成真实 LLM API 调用。
"""

from typing import Dict, List, Set


# 一条聊天消息的数据结构：
# {
#     "role": "user" 或 "assistant",
#     "content": "消息内容"
# }
Message = Dict[str, str]


# 每个场景额外补充一些关键词。
# 这些关键词用于判断用户回答是否和当前场景相关。
SCENE_EXTRA_TERMS = {
    "Job Interview": {
        "student",
        "major",
        "computer",
        "science",
        "backend",
        "frontend",
        "developer",
        "python",
        "java",
        "project",
        "internship",
        "skill",
        "strength",
        "weakness",
        "resume",
        "company",
        "position",
        "experience",
        "challenge",
        "team",
    },
    "Restaurant Ordering": {
        "table",
        "reservation",
        "menu",
        "food",
        "drink",
        "recommend",
        "order",
        "dish",
        "water",
        "coffee",
        "tea",
        "bill",
        "pay",
        "restaurant",
        "waiter",
        "spicy",
    },
    "Business Meeting": {
        "progress",
        "deadline",
        "issue",
        "problem",
        "solution",
        "plan",
        "task",
        "update",
        "team",
        "meeting",
        "risk",
        "next",
        "step",
        "schedule",
        "delay",
    },
}


def normalize_text(text: str) -> str:
    """
    将文本统一转成小写，并去掉前后空格。

    这样做是为了让关键词匹配更稳定。
    例如 Python、python、PYTHON 都会被当成 python。
    """

    return text.strip().lower()


def get_user_messages(chat_history: List[Message]) -> List[str]:
    """
    从聊天记录中取出所有用户说过的话。
    """

    return [
        message["content"]
        for message in chat_history
        if message.get("role") == "user"
    ]


def get_latest_user_message(chat_history: List[Message]) -> str:
    """
    获取用户最近一次输入的回答。
    """

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return ""

    return user_messages[-1]


def build_relevance_terms(scene: Dict) -> Set[str]:
    """
    构建当前场景的相关关键词集合。

    关键词来源有三类：
    1. scenes.yaml 里面配置的 keywords；
    2. scenes.yaml 里面 goals 中的重要单词；
    3. 当前文件中额外补充的场景关键词。
    """

    scene_name = scene.get("name", "")
    terms = set()

    # 加入 scenes.yaml 中配置的关键词。
    for keyword in scene.get("keywords", []):
        terms.add(keyword.lower())

    # 从 goals 中提取一些较长的词，作为相关词。
    for goal in scene.get("goals", []):
        for word in goal.lower().replace("-", " ").split():
            if len(word) >= 4:
                terms.add(word)

    # 加入每个场景额外补充的关键词。
    terms.update(SCENE_EXTRA_TERMS.get(scene_name, set()))

    return terms


def contains_any_term(text: str, terms: Set[str]) -> bool:
    """
    判断用户回答里是否包含当前场景相关关键词。
    """

    normalized_text = normalize_text(text)

    for term in terms:
        if term in normalized_text:
            return True

    return False


def is_answer_too_short(text: str) -> bool:
    """
    判断用户回答是否过短。

    对于口语训练来说，只回答 Yes、No、OK 之类的内容，
    很难达到练习效果，所以需要引导用户补充完整句子。
    """

    return len(text.split()) < 5


def choose_next_goal(scene: Dict, user_turn_count: int) -> str:
    """
    根据用户当前回答轮次，选择一个合适的场景目标。

    这个函数用于在用户偏题时，把对话拉回场景任务。
    """

    goals = scene.get("goals", [])

    if not goals:
        return "give a more detailed answer"

    goal_index = min(user_turn_count, len(goals) - 1)

    return goals[goal_index]


def build_short_answer_reply(scene: Dict) -> str:
    """
    当用户回答太短时，生成引导补充的回复。
    """

    return (
        "Your answer is understandable, but it is a little short. "
        f"Could you add one complete sentence related to {scene['name']}?"
    )


def build_off_topic_reply(scene: Dict, user_turn_count: int) -> str:
    """
    当用户回答明显偏离场景时，生成拉回场景的回复。
    """

    next_goal = choose_next_goal(scene, user_turn_count)

    return (
        f"I see. Let's bring the conversation back to the {scene['name']} scenario. "
        f"Could you try to {next_goal}?"
    )


def build_job_interview_reply(answer: str) -> str:
    """
    根据面试场景下的用户回答，生成更具体的追问。
    """

    normalized_answer = normalize_text(answer)

    if any(word in normalized_answer for word in ["project", "system", "app", "website"]):
        return (
            "That sounds like a useful project. "
            "What was your responsibility in that project, and what challenge did you solve?"
        )

    if any(word in normalized_answer for word in ["python", "java", "backend", "frontend"]):
        return (
            "Good. Could you describe one specific project where you used that skill?"
        )

    if any(word in normalized_answer for word in ["challenge", "problem", "difficult", "issue"]):
        return (
            "Good point. How did you solve that challenge, and what did you learn from it?"
        )

    if any(word in normalized_answer for word in ["team", "teamwork", "collaborate"]):
        return (
            "Teamwork is important. Could you give an example of how you worked with others?"
        )

    return (
        "Thanks for sharing. Could you give one specific example to make your answer stronger?"
    )


def build_restaurant_reply(answer: str) -> str:
    """
    根据点餐场景下的用户回答，生成更具体的追问。
    """

    normalized_answer = normalize_text(answer)

    if "reservation" in normalized_answer or "table" in normalized_answer:
        return "Sure. How many people are in your party, and what time would you like the table?"

    if "menu" in normalized_answer or "recommend" in normalized_answer:
        return "Of course. Do you prefer something spicy, light, or vegetarian?"

    if "order" in normalized_answer or "food" in normalized_answer or "dish" in normalized_answer:
        return "Great choice. Would you like anything to drink with that?"

    if "bill" in normalized_answer or "pay" in normalized_answer:
        return "Sure. Would you like to pay by cash or card?"

    return "No problem. Could you tell me what you would like to order?"


def build_business_meeting_reply(answer: str) -> str:
    """
    根据会议场景下的用户回答，生成更具体的追问。
    """

    normalized_answer = normalize_text(answer)

    if "progress" in normalized_answer or "update" in normalized_answer:
        return "Thanks for the update. Are there any blockers or risks we should discuss?"

    if "problem" in normalized_answer or "issue" in normalized_answer or "delay" in normalized_answer:
        return "I understand. What solution do you suggest, and what support do you need?"

    if "solution" in normalized_answer or "plan" in normalized_answer:
        return "That sounds reasonable. What are the next steps and expected timeline?"

    if "deadline" in normalized_answer or "schedule" in normalized_answer:
        return "Thanks. Do you think the current deadline is still realistic?"

    return "Thanks. Could you make your update more specific with one concrete next step?"


def build_scene_specific_reply(scene: Dict, answer: str) -> str:
    """
    根据不同场景，调用不同的追问生成函数。
    """

    scene_name = scene.get("name", "")

    if scene_name == "Job Interview":
        return build_job_interview_reply(answer)

    if scene_name == "Restaurant Ordering":
        return build_restaurant_reply(answer)

    if scene_name == "Business Meeting":
        return build_business_meeting_reply(answer)

    return "Thanks for sharing. Could you give one more specific example?"


def generate_mock_ai_reply(scene: Dict, chat_history: List[Message]) -> str:
    """
    生成 AI 教练回复。

    当前是规则版 mock 回复，但已经具备轻量上下文判断能力：
    1. 判断回答是否太短；
    2. 判断回答是否和当前场景相关；
    3. 根据不同场景生成不同追问。

    后续接入真实大模型时，可以优先替换这个函数。
    """

    latest_answer = get_latest_user_message(chat_history)
    user_turn_count = len(get_user_messages(chat_history))

    if not latest_answer:
        return scene["opening_message"]

    if is_answer_too_short(latest_answer):
        return build_short_answer_reply(scene)

    relevance_terms = build_relevance_terms(scene)

    if not contains_any_term(latest_answer, relevance_terms):
        return build_off_topic_reply(scene, user_turn_count)

    return build_scene_specific_reply(scene, latest_answer)
