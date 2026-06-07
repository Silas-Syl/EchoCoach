"""
EchoCoach 应用入口文件。

负责：
1. 创建 Gradio 页面；
2. 加载练习场景；
3. 处理开始练习、发送回答、录音确认、结束练习；
4. 调用 services 中的业务模块生成 AI 回复、纠错反馈、能力评分和课后报告。
"""
from services.speech_service import speech_to_text, text_to_speech
import gradio as gr

from services.scene_service import load_scenes
from services.coach_service import generate_ai_reply
from services.correction_service import correct_sentence, format_correction_history
from services.scoring_service import generate_scores
from services.report_service import generate_report


scenes = load_scenes()

DEFAULT_SCENE_ID = "job_interview" if "job_interview" in scenes else list(scenes.keys())[0]


def get_scene(scene_id):
    """安全获取场景配置。"""

    if scene_id in scenes:
        return scenes[scene_id]

    return scenes[DEFAULT_SCENE_ID]


def start_practice(scene_id):
    """
    开始一次新的口语练习。

    返回值顺序必须与 start_button.click(outputs=[...]) 完全一致：
    1. chatbot
    2. chat_history_state
    3. current_scene
    4. corrections_state
    5. score_state
    6. status_box
    7. user_input
    8. correction_box
    9. correction_history_box
    10. score_box
    11. report_box
    """

    if not scene_id:
        scene_id = DEFAULT_SCENE_ID

    scene = get_scene(scene_id)

    opening_message = scene.get(
        "opening_message",
        f"Welcome to the {scene.get('name', 'English Practice')} practice. Let's begin."
    )

    chat_history = [
        {
            "role": "assistant",
            "content": opening_message,
        }
    ]

    corrections = []
    score = None

    status = f"✅ 已开始场景：{scene.get('name', scene_id)}，请在下方输入英文回答。"

    return (
        chat_history,
        chat_history,
        scene_id,
        corrections,
        score,
        status,
        "",
        None,
        "暂无历史错误记录。",
        score,
        "练习结束后，这里会生成本次口语练习总结。",
    )


def send_message(user_text, chat_history, current_scene_id, corrections, current_score):
    """
    处理用户输入的英文回答，并生成：
    1. AI 动态追问；
    2. 本轮纠错；
    3. 历史错误记录；
    4. 当前能力评分。

    返回值顺序必须与 send_button.click(outputs=[...]) 完全一致：
    1. chatbot
    2. chat_history_state
    3. user_input
    4. correction_box
    5. correction_history_box
    6. corrections_state
    7. score_box
    8. score_state
    9. status_box
    """

    if chat_history is None:
        chat_history = []

    if corrections is None:
        corrections = []

    if not current_scene_id:
        current_scene_id = DEFAULT_SCENE_ID

    scene = get_scene(current_scene_id)

    if not user_text or not user_text.strip():
        return (
            chat_history,
            chat_history,
            "",
            None,
            format_correction_history(corrections),
            corrections,
            current_score,
            current_score,
            "⚠️ 请先输入一句英文回答。",
        )

    cleaned_user_text = user_text.strip()

    chat_history = chat_history + [
        {
            "role": "user",
            "content": cleaned_user_text,
        }
    ]

    correction_result = correct_sentence(cleaned_user_text)
    corrections = corrections + [correction_result]

    ai_reply = generate_ai_reply(
        scene=scene,
        chat_history=chat_history,
        user_message=None,
    )
    try:
        ai_audio_path = text_to_speech(ai_reply)
    except Exception as error:
        print("TTS error:", error)
        ai_audio_path = None
    

    chat_history = chat_history + [
        {
            "role": "assistant",
            "content": ai_reply,
        }
    ]

    score_feedback = generate_scores(scene, chat_history, corrections)

    user_turn_count = len([
        message for message in chat_history
        if isinstance(message, dict) and message.get("role") == "user"
    ])

    status = f"🎯 正在练习场景：{scene.get('name', current_scene_id)} | 已完成 {user_turn_count} 轮"

    return (
        chat_history,
        chat_history,
        "",
        correction_result,
        format_correction_history(corrections),
        corrections,
        score_feedback,
        score_feedback,
        ai_audio_path,
        status,
    )


def handle_audio_record(audio):
    """
    处理用户录音。

    当前轻量版：
    1. 只确认是否收到录音文件；
    2. 暂时不做 ASR；
    3. 用户继续在文本框中手动输入英文。
    """

    if audio is None:
        return "⚠️ 未检测到录音，请重试。"

    return "✅ 已收到录音文件。当前版本请在文本框中确认或输入识别内容，然后点击发送。"

def handle_audio_and_send(audio, chat_history, current_scene_id, corrections, current_score):
    """
    录音 → ASR 识别 → 自动发送 → AI 回复 → AI 语音回答
    """

    if chat_history is None:
        chat_history = []

    if corrections is None:
        corrections = []

    if audio is None:
        return (
            chat_history,
            chat_history,
            None,
            "",
            "",
            None,
            format_correction_history(corrections),
            corrections,
            current_score,
            current_score,
            None,
            "⚠️ 未检测到录音，请重试。",
            "⚠️ 未检测到录音，请重试。",
        )

    try:
        transcript = speech_to_text(audio)

        if not transcript:
            return (
                chat_history,
                chat_history,
                None,
                "",
                "",
                None,
                format_correction_history(corrections),
                corrections,
                current_score,
                current_score,
                None,
                "⚠️ 没有识别到有效英文内容，请重新录音。",
                "⚠️ 没有识别到有效英文内容，请重新录音。",
            )

        result = send_message(
            transcript,
            chat_history,
            current_scene_id,
            corrections,
            current_score,
        )

        return (
            result[0],       # chatbot
            result[1],       # chat_history_state
            None,            # audio_input，清空录音，方便继续录下一句
            "",              # user_input
            transcript,      # recognized_text_box
            result[3],       # correction_box
            result[4],       # correction_history_box
            result[5],       # corrections_state
            result[6],       # score_box
            result[7],       # score_state
            result[8],       # ai_audio_output
            result[9],       # status_box
            f"✅ 已识别并发送：{transcript}",
        )

    except Exception as error:
        return (
            chat_history,
            chat_history,
            None,
            "",
            "",
            None,
            format_correction_history(corrections),
            corrections,
            current_score,
            current_score,
            None,
            f"❌ 语音处理失败：{error}",
            f"❌ 语音处理失败：{error}",
        )


def end_practice(chat_history, current_scene_id, corrections, score):
    """
    结束练习，生成个性化课后总结报告。

    返回值顺序必须与 end_button.click(outputs=[...]) 完全一致：
    1. report_box
    2. status_box
    """

    if not chat_history or len(chat_history) <= 1:
        return (
            "练习内容不足，请至少完成一轮对话后再结束。",
            "⚠️ 练习内容不足，无法生成报告。",
        )

    if not current_scene_id:
        current_scene_id = DEFAULT_SCENE_ID

    scene = get_scene(current_scene_id)

    if corrections is None:
        corrections = []

    report = generate_report(scene, chat_history, corrections, score)

    return (
        report,
        "✅ 练习已结束，课后总结已生成。",
    )


with gr.Blocks(title="EchoCoach") as demo:

    gr.Markdown("# 🎙️ EchoCoach — AI 场景化英语口语陪练")
    gr.Markdown(
        "选择场景 → 开始练习 → 输入英文回答 → 获得 AI 追问 + 纠错 + 评分 → 结束后查看总结报告"
    )

    current_scene = gr.State(DEFAULT_SCENE_ID)
    corrections_state = gr.State([])
    chat_history_state = gr.State([])
    score_state = gr.State(None)

    status_box = gr.Textbox(
        label="当前状态",
        value="请选择场景并点击「开始练习」。",
        interactive=False,
    )

    with gr.Row():

        with gr.Column(scale=3):

            scene_dropdown = gr.Dropdown(
                choices=list(scenes.keys()),
                value=DEFAULT_SCENE_ID,
                label="选择练习场景",
            )

            start_button = gr.Button("▶️ 开始练习", variant="primary")

            chatbot = gr.Chatbot(
                label="对话区",
                height=420,
            )

            user_input = gr.Textbox(
                label="你的英文回答",
                placeholder="请在这里输入英文，例如：I very like backend development.",
                lines=2,
            )

            with gr.Row():
                send_button = gr.Button("📨 发送回答", variant="primary", scale=3)
                end_button = gr.Button("🔚 结束练习", variant="stop", scale=1)

            gr.Markdown("### 🎤 语音输入")

            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="录音（录完后点击确认）",
            )

            confirm_audio_button = gr.Button("✅ 确认录音")

            audio_status = gr.Textbox(
                label="录音状态",
                interactive=False,
                value="等待录音...",
            )

            recognized_text_box = gr.Textbox(
                label="语音识别结果",
                interactive=False,
                placeholder="录音识别出的英文会显示在这里。"
            )

            ai_audio_output = gr.Audio(
                label="🔊 AI 语音回答",
                autoplay=True,
                interactive=False
            )


        with gr.Column(scale=2):

            correction_box = gr.JSON(
                label="📝 本轮纠错反馈",
            )

            correction_history_box = gr.Markdown(
                label="📚 历史错误记录",
                value="暂无历史错误记录。",
            )

            score_box = gr.JSON(
                label="📊 当前能力评分",
            )

            report_box = gr.Markdown(
                label="📋 课后总结报告",
                value="练习结束后，这里会生成本次口语练习总结。",
            )

    start_button.click(
        fn=start_practice,
        inputs=[scene_dropdown],
        outputs=[
            chatbot,
            chat_history_state,
            current_scene,
            corrections_state,
            score_state,
            status_box,
            user_input,
            correction_box,
            correction_history_box,
            score_box,
            report_box,
        ],
    )

    send_button.click(
        fn=send_message,
        inputs=[
            user_input,
            chat_history_state,
            current_scene,
            corrections_state,
            score_state,
        ],
        outputs=[
            chatbot,
            chat_history_state,
            user_input,
            correction_box,
            correction_history_box,
            corrections_state,
            score_box,
            score_state,
            ai_audio_output,
            status_box,
        ],
    )

    user_input.submit(
        fn=send_message,
        inputs=[
            user_input,
            chat_history_state,
            current_scene,
            corrections_state,
            score_state,
        ],
        outputs=[
            chatbot,
            chat_history_state,
            user_input,
            correction_box,
            correction_history_box,
            corrections_state,
            score_box,
            score_state,
            ai_audio_output,
            status_box,
        ],
    )

    confirm_audio_button.click(
        fn=handle_audio_and_send,
        inputs=[
            audio_input,
            chat_history_state,
            current_scene,
            corrections_state,
            score_state,
        ],
        outputs=[
            
            chatbot,
            chat_history_state,
            audio_input,
            user_input,
            recognized_text_box,
            correction_box,
            correction_history_box,
            corrections_state,
            score_box,
            score_state,
            ai_audio_output,
            status_box,
            audio_status,
        ],
    )


    end_button.click(
        fn=end_practice,
        inputs=[
            chat_history_state,
            current_scene,
            corrections_state,
            score_state,
        ],
        outputs=[
            report_box,
            status_box,
        ],
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
