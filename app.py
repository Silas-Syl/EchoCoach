"""
EchoCoach 应用入口文件。

这个文件负责：
1. 创建 Gradio 页面；
2. 加载练习场景；
3. 处理用户点击按钮、输入英文回答等页面事件；
4. 调用 services 中的业务模块生成 AI 回复、纠错反馈和能力评分。

注意：
app.py 只负责页面和流程控制。
具体业务逻辑尽量放到 services 文件夹中，避免 app.py 变得过长。
"""

import gradio as gr

from services.scene_service import load_scenes
from services.coach_service import generate_mock_ai_reply
from services.correction_service import correct_sentence
from services.scoring_service import generate_scores


# 程序启动时加载所有场景配置。
# scenes 的数据来自 data/scenes.yaml。
scenes = load_scenes()


def start_practice(scene_id):
    """
    开始一次新的口语练习。

    参数：
        scene_id: 用户在下拉框中选择的场景 ID，例如 job_interview。

    返回：
        chatbot_display: 显示在页面对话区的聊天记录。
        chat_history_state: 保存到 Gradio State 的原始聊天记录。
        current_scene_id: 当前场景 ID。
        corrections: 当前练习的纠错记录，开始时为空。
        status: 当前练习状态提示。
        user_input: 清空输入框。
        correction_feedback: 清空纠错反馈区。
        score_feedback: 清空评分区。
    """

    scene = scenes[scene_id]

    chat_history = [
        {
            "role": "assistant",
            "content": scene["opening_message"]
        }
    ]

    corrections = []
    status = f"已开始场景：{scene['name']}"

    return chat_history, chat_history, scene_id, corrections, status, "", None, None


def send_message(user_text, chat_history, current_scene_id, corrections):
    """
    处理用户输入的英文回答，并生成 AI 追问、纠错反馈和能力评分。

    这里的 chat_history 来自 chat_history_state，
    而不是直接来自 Chatbot 组件。

    这样做可以避免 Gradio Chatbot 在多轮对话时改变数据格式，
    导致评分模块拿到错误的数据类型。
    """

    # 如果聊天记录为空，先初始化为空列表。
    if chat_history is None:
        chat_history = []

    # 如果纠错记录为空，初始化为空列表。
    if corrections is None:
        corrections = []

    # 如果页面状态中没有场景 ID，就默认使用面试场景。
    if not current_scene_id:
        current_scene_id = "job_interview"

    scene = scenes[current_scene_id]

    # 用户没有输入内容时，不生成 AI 回复，只给出提示。
    if not user_text or not user_text.strip():
        status = "请先输入一句英文回答。"
        return chat_history, chat_history, "", None, corrections, None, status

    cleaned_user_text = user_text.strip()

    # 1. 把用户回答加入原始聊天记录。
    chat_history.append(
        {
            "role": "user",
            "content": cleaned_user_text
        }
    )

    # 2. 对用户回答进行轻量纠错。
    correction_feedback = correct_sentence(cleaned_user_text)
    corrections.append(correction_feedback)

    # 3. 根据当前场景和原始聊天记录，生成 AI 教练追问。
    ai_reply = generate_mock_ai_reply(scene, chat_history)

    # 4. 把 AI 回复加入原始聊天记录。
    chat_history.append(
        {
            "role": "assistant",
            "content": ai_reply
        }
    )

    # 5. 根据原始聊天记录和纠错记录，生成轻量能力评分。
    score_feedback = generate_scores(scene, chat_history, corrections)

    status = f"正在练习场景：{scene['name']}"

    return chat_history, chat_history, "", correction_feedback, corrections, score_feedback, status


with gr.Blocks(title="EchoCoach") as demo:
    gr.Markdown("# EchoCoach - AI 场景化英语口语陪练")
    gr.Markdown(
        """
        这是一个轻量版 MVP，用于在真实场景中练习英语口语。

        当前版本支持：
        - 选择练习场景
        - AI 英文开场
        - 用户输入英文回答
        - AI 根据回答进行简单追问
        - 系统给出语法 / 表达纠错反馈
        - 系统生成轻量口语能力评分
        """
    )

    # 保存当前练习场景。
    current_scene = gr.State("job_interview")

    # 保存本次练习的所有纠错记录。
    corrections_state = gr.State([])

    # 保存原始聊天记录。
    # 注意：不要直接把 Chatbot 组件的值当成真实数据源。
    chat_history_state = gr.State([])

    scene_dropdown = gr.Dropdown(
        choices=list(scenes.keys()),
        value="job_interview",
        label="选择练习场景"
    )

    start_button = gr.Button("开始练习")

    status_box = gr.Textbox(
        label="当前状态",
        interactive=False
    )

    chatbot = gr.Chatbot(
        label="对话区"
    )

    user_input = gr.Textbox(
        label="你的英文回答",
        placeholder="请在这里输入英文，例如：I very like backend development."
    )

    send_button = gr.Button("发送回答")

    correction_box = gr.JSON(
        label="本轮纠错反馈"
    )

    score_box = gr.JSON(
        label="当前能力评分"
    )

    start_button.click(
        fn=start_practice,
        inputs=scene_dropdown,
        outputs=[
            chatbot,
            chat_history_state,
            current_scene,
            corrections_state,
            status_box,
            user_input,
            correction_box,
            score_box
        ]
    )

    send_button.click(
        fn=send_message,
        inputs=[
            user_input,
            chat_history_state,
            current_scene,
            corrections_state
        ],
        outputs=[
            chatbot,
            chat_history_state,
            user_input,
            correction_box,
            corrections_state,
            score_box,
            status_box
        ]
    )

    # 支持用户在输入框中按 Enter 直接发送。
    user_input.submit(
        fn=send_message,
        inputs=[
            user_input,
            chat_history_state,
            current_scene,
            corrections_state
        ],
        outputs=[
            chatbot,
            chat_history_state,
            user_input,
            correction_box,
            corrections_state,
            score_box,
            status_box
        ]
    )


if __name__ == "__main__":
    demo.launch()

