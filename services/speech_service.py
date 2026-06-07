"""
语音服务模块。

负责：
1. ASR：把用户录音转成英文文本；
2. TTS：把 AI 回复转成语音文件；
3. 失败时不让 Demo 崩溃。
"""

import os
import base64
import mimetypes
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_OUTPUT_DIR = BASE_DIR / "outputs" / "audio"
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _get_api_key():
    """
    优先使用 DASHSCOPE_API_KEY。
    如果没有，就复用 LLM_API_KEY。
    """

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY")

    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY 或 LLM_API_KEY，请检查 .env 文件")

    return api_key


def _guess_mime_type(audio_path):
    """
    根据音频文件后缀判断 MIME 类型。
    """

    mime_type, _ = mimetypes.guess_type(audio_path)

    if mime_type:
        return mime_type

    suffix = Path(audio_path).suffix.lower()

    if suffix == ".wav":
        return "audio/wav"

    if suffix == ".mp3":
        return "audio/mpeg"

    if suffix == ".m4a":
        return "audio/mp4"

    if suffix == ".webm":
        return "audio/webm"

    return "audio/wav"


def speech_to_text(audio_path):
    """
    把录音文件转成英文文本。

    使用 DashScope OpenAI-compatible chat/completions 接口。
    """

    if not audio_path:
        raise RuntimeError("没有收到录音文件")

    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise RuntimeError(f"录音文件不存在：{audio_path}")

    api_url = os.getenv(
        "ASR_API_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    model = os.getenv("ASR_MODEL", "qwen3-asr-flash")
    language = os.getenv("ASR_LANGUAGE", "en")
    api_key = _get_api_key()

    mime_type = _guess_mime_type(str(audio_file))
    audio_base64 = base64.b64encode(audio_file.read_bytes()).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{audio_base64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": data_uri
                        }
                    }
                ]
            }
        ],
        "stream": False,
        "asr_options": {
            "language": language,
            "enable_itn": False
        }
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()
    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(item["text"])
            return " ".join(texts).strip()

        return str(content).strip()

    except Exception as error:
        raise RuntimeError(f"无法解析 ASR 返回结果：{data}") from error


def text_to_speech(text):
    """
    把 AI 英文回复转成语音文件。

    返回本地音频文件路径，供 Gradio Audio 播放。
    """

    if not text or not text.strip():
        return None

    api_url = os.getenv(
        "TTS_API_URL",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )
    model = os.getenv("TTS_MODEL", "qwen3-tts-flash")
    voice = os.getenv("TTS_VOICE", "Cherry")
    language_type = os.getenv("TTS_LANGUAGE", "English")
    api_key = _get_api_key()

    payload = {
        "model": model,
        "input": {
            "text": text.strip(),
            "voice": voice,
            "language_type": language_type
        }
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()
    data = response.json()

    try:
        audio_url = data["output"]["audio"]["url"]
    except Exception as error:
        raise RuntimeError(f"无法解析 TTS 返回结果：{data}") from error

    audio_response = requests.get(audio_url, timeout=90)
    audio_response.raise_for_status()

    output_path = AUDIO_OUTPUT_DIR / f"ai_reply_{uuid.uuid4().hex}.wav"
    output_path.write_bytes(audio_response.content)

    return str(output_path)
