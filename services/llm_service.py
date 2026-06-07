import os
import json
import requests
from dotenv import load_dotenv


load_dotenv()


def _get_required_env(name):
    """读取必要环境变量。"""

    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"缺少 {name}，请检查 .env 文件")

    return value


def _debug_enabled():
    """是否开启 LLM 调试日志。"""

    return os.getenv("DEBUG_LLM", "0") == "1"


def call_llm(messages, temperature=0.7):
    """
    调用兼容 OpenAI 格式的大模型接口。

    .env 示例：
    LLM_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    LLM_API_KEY=your_bailian_api_key
    LLM_MODEL=deepseek-v4-flash
    """

    api_url = _get_required_env("LLM_API_URL")
    api_key = _get_required_env("LLM_API_KEY")
    model = _get_required_env("LLM_MODEL")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60,
        )

        if _debug_enabled():
            print("LLM status code:", response.status_code)

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout as error:
        raise RuntimeError("大模型请求超时，请稍后重试。") from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"大模型请求失败：{error}") from error

    except json.JSONDecodeError as error:
        raise RuntimeError("大模型返回内容不是合法 JSON。") from error

    try:
        return data["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"大模型返回格式异常：{data}") from error


def _clean_json_text(content):
    """
    清理模型返回的 JSON 文本。

    兼容：
    1. ```json 包裹
    2. ``` 包裹
    3. JSON 前后有解释文字
    """

    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    return cleaned


def call_llm_json(messages, temperature=0.3):
    """
    调用大模型，并解析 JSON 返回。
    """

    content = call_llm(messages, temperature=temperature)
    cleaned = _clean_json_text(content)

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError as error:
        raise RuntimeError(f"无法解析模型返回的 JSON：{cleaned}") from error
