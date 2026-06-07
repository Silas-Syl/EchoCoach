"""
场景加载服务。

优先读取：
1. data/scenes.yaml
2. 项目根目录 scenes.yaml

如果文件不存在或读取失败，使用内置默认场景，避免 Demo 启动崩溃。
"""

from pathlib import Path
import yaml


BASE_DIR = Path(__file__).resolve().parent.parent

SCENE_FILE_CANDIDATES = [
    BASE_DIR / "data" / "scenes.yaml",
    BASE_DIR / "scenes.yaml",
]


DEFAULT_SCENES = {
    "job_interview": {
        "name": "Job Interview",
        "ai_role": "Interviewer",
        "user_role": "Candidate",
        "difficulty": "B1-B2",
        "opening_message": "Hi, welcome to the interview. Could you briefly introduce yourself?",
        "goals": [
            "introduce yourself",
            "describe one project experience",
            "explain a challenge you solved",
            "ask one question to the interviewer",
        ],
        "keywords": [
            "experience",
            "project",
            "challenge",
            "teamwork",
            "responsibility",
        ],
    },
    "restaurant_ordering": {
        "name": "Restaurant Ordering",
        "ai_role": "Waiter",
        "user_role": "Customer",
        "difficulty": "A2-B1",
        "opening_message": "Good evening! Welcome to our restaurant. Do you have a reservation?",
        "goals": [
            "ask for a table",
            "order food and drinks",
            "ask about recommendations",
            "pay the bill",
        ],
        "keywords": [
            "menu",
            "recommend",
            "order",
            "bill",
            "reservation",
        ],
    },
    "business_meeting": {
        "name": "Business Meeting",
        "ai_role": "Meeting Host",
        "user_role": "Team Member",
        "difficulty": "B1-B2",
        "opening_message": "Thanks for joining today's meeting. Could you give us a quick update on your progress?",
        "goals": [
            "give a progress update",
            "explain a problem",
            "suggest a solution",
            "respond to follow-up questions",
        ],
        "keywords": [
            "progress",
            "deadline",
            "issue",
            "solution",
            "next step",
        ],
    },
}


def _validate_scenes(data):
    """简单校验 scenes.yaml 读取结果。"""

    if not isinstance(data, dict):
        return None

    valid_scenes = {}

    for scene_id, scene in data.items():
        if not isinstance(scene, dict):
            continue

        scene.setdefault("name", str(scene_id))
        scene.setdefault("ai_role", "English speaking coach")
        scene.setdefault("user_role", "English learner")
        scene.setdefault("difficulty", "B1-B2")
        scene.setdefault(
            "opening_message",
            f"Welcome to the {scene.get('name', scene_id)} practice. Let's begin."
        )
        scene.setdefault("goals", [])
        scene.setdefault("keywords", [])

        valid_scenes[scene_id] = scene

    if not valid_scenes:
        return None

    return valid_scenes


def load_scenes():
    """
    加载所有练习场景。

    返回格式：
    {
        "job_interview": {...},
        "restaurant_ordering": {...},
        "business_meeting": {...}
    }
    """

    for scene_file in SCENE_FILE_CANDIDATES:
        if not scene_file.exists():
            continue

        try:
            with open(scene_file, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)

            scenes = _validate_scenes(data)

            if scenes:
                return scenes

        except Exception as error:
            print(f"Load scenes failed from {scene_file}: {error}")

    return DEFAULT_SCENES
