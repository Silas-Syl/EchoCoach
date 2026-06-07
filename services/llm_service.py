import os
import json
import requests
from dotenv import load_dotenv


# 加载 .env 文件里的环境变量
load_dotenv()


def call_llm(messages, temperature=0.7):
    """
    调用外部大模型。

    messages 格式示例：
    [
        {"role": "system", "content": "You are an English speaking coach."},
        {"role": "user", "content": "I very like backend."}
    ]
    """

    api_url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not api_url:
        raise RuntimeError("缺少 LLM_API_URL，请检查 .env 文件")

    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY，请检查 .env 文件")

    if not model:
        raise RuntimeError("缺少 LLM_MODEL，请检查 .env 文件")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=60
    )

    print(response.status_code, response.text)
    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def call_llm_json(messages, temperature=0.3):
    """
    调用大模型，并要求它返回 JSON。

    这个函数会处理模型返回 ```json ... ``` 的情况。
    """

    content = call_llm(messages, temperature=temperature)

    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()

    # 防止模型前后多说废话，只截取 JSON 主体
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]

    return json.loads(cleaned)
