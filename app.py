"""
EchoCoach 应用入口文件。

负责：
1. 创建 Gradio 页面；
2. 加载练习场景；
3. 处理用户输入；
4. 调用对话、纠错、评分和报告模块。
"""

import os
import gradio as gr

from services.scene_service import load_scenes
from services.coach_service import generate_mock_ai_reply
from services.correction_service import correct_sentence
from services.scoring_service import generate_scores
from services.report_service import generate_report


scenes = load_scenes()

DEFAULT_SCENE_ID = "job_interview"


def get_scene(scene_id):
    """安全获取场景，避免 scene_id 为空或不存在时报错。"""

    if scene_id and scene_id in scenes:
        return scene_id, scenes[scene_id]

    if DEFAULT_SCENE_ID in scenes:
        return DEFAULT_SCENE_ID, scenes[DEFAULT_SCENE_ID]

    first_scene_id = list(scenes.keys())[0]
    return first_scene_id, scenes[first_scene_id]


def build_chatbot_display(chat_history):
    """
    将聊天记录整理成 Gradio Chatbot 当前需要的 messages 格式。

    注意：
    这里不能返回 [用户消息, AI消息] 这种旧版二元组格式。
    当前页面报错说明你的 Gradio Chatbot 需要的是 role/content 格式。
    """

    if chat_history is None:
        return []

    display_messages = []

    for message in chat_history:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content", "")

        if role not in ["user", "assistant"]:
            continue

        display_messages.append(
            {
                "role": role,
                "content": str(content)
            }
        )

    return display_messages


def start_practice(scene_id):
    """开始一次新的口语练习。"""

    scene_id, scene = get_scene(scene_id)

    chat_history = [
        {
            "role": "assistant",
            "content": scene["opening_message"]
        }
    ]

    corrections = []
    status = f"已开始场景：{scene['name']}"

    chatbot_display = build_chatbot_display(chat_history)

    return (
        chatbot_display,
        chat_history,
        scene_id,
        corrections,
        status,
        "",
        None,
        None,
        None
    )


def send_message(user_text, chat_history, current_scene_id, corrections):
    """处理用户回答，并生成 AI 回复、纠错反馈和评分。"""

    if chat_history is None:
        chat_history = []
    else:
        chat_history = list(chat_history)

    if corrections is None:
        corrections = []
    else:
        corrections = list(corrections)

    current_scene_id, scene = get_scene(current_scene_id)

    if not user_text or not user_text.strip():
        status = "请先输入一句英文回答。"
        chatbot_display = build_chatbot_display(chat_history)

        return (
            chatbot_display,
            chat_history,
            "",
            None,
            corrections,
            None,
            status
        )

    cleaned_user_text = user_text.strip()

    chat_history.append(
        {
            "role": "user",
            "content": cleaned_user_text
        }
    )

    correction_feedback = correct_sentence(cleaned_user_text)
    corrections.append(correction_feedback)

    ai_reply = generate_mock_ai_reply(scene, chat_history)

    chat_history.append(
        {
            "role": "assistant",
            "content": ai_reply
        }
    )

    score_feedback = generate_scores(scene, chat_history, corrections)
    status = f"正在练习场景：{scene['name']}"

    chatbot_display = build_chatbot_display(chat_history)

    return (
        chatbot_display,
        chat_history,
        "",
        correction_feedback,
        corrections,
        score_feedback,
        status
    )


def finish_practice(chat_history, current_scene_id, corrections):
    """结束练习并生成课后总结报告。"""

    if chat_history is None:
        chat_history = []

    if corrections is None:
        corrections = []

    current_scene_id, scene = get_scene(current_scene_id)

    user_turn_count = len(
        [
            message
            for message in chat_history
            if isinstance(message, dict) and message.get("role") == "user"
        ]
    )

    if user_turn_count == 0:
        return None, "请至少完成一轮英文回答后再生成报告。"

    report = generate_report(scene, chat_history, corrections)

    return report, "课后总结报告已生成。"

def handle_audio_record(audio_file):
    """处理用户录音文件。当前版本先确认录音可用，下一步再接入 ASR。"""

    if audio_file is None:
        return "还没有检测到录音，请先点击麦克风录一段英文。"

    try:
        file_size_kb = os.path.getsize(audio_file) / 1024
        file_name = os.path.basename(audio_file)
        return (
            f"已收到录音文件：{file_name}，大小约 {file_size_kb:.1f} KB。\n"
            "当前版本请在下方文本框手动输入你刚才说的英文内容。下一步会接入语音识别自动转写。"
        )
    except Exception as error:
        return f"录音文件读取失败：{error}"


with gr.Blocks(title="EchoCoach") as demo:
    gr.Markdown("# EchoCoach - AI 场景化英语口语陪练")
    gr.Markdown(
        """
        当前版本支持：
        - 场景选择
        - AI 英文对话
        - 语法 / 表达纠错
        - 轻量口语评分
        - 课后总结报告
        """
    )

    current_scene = gr.State(DEFAULT_SCENE_ID)
    corrections_state = gr.State([])
    chat_history_state = gr.State([])

    scene_dropdown = gr.Dropdown(
        choices=list(scenes.keys()),
        value=DEFAULT_SCENE_ID if DEFAULT_SCENE_ID in scenes else list(scenes.keys())[0],
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

    gr.Markdown("## 语音输入")

    audio_input = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="录制你的英文回答"
    )

    audio_check_button = gr.Button("确认录音")

    audio_status_box = gr.Textbox(
        label="录音状态",
        interactive=False
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

    finish_button = gr.Button("结束练习并生成报告")

    report_box = gr.JSON(
        label="课后总结报告"
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
            score_box,
            report_box
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

    finish_button.click(
        fn=finish_practice,
        inputs=[
            chat_history_state,
            current_scene,
            corrections_state
        ],
        outputs=[
            report_box,
            status_box
        ]
    )

    audio_check_button.click(
        fn=handle_audio_record,
        inputs=[audio_input],
        outputs=[audio_status_box]
    )


if __name__ == "__main__":
    demo.launch()
