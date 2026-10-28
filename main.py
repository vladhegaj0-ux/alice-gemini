import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.8-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

async def query_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "В настройках Render не указан GEMINI_API_KEY."

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 180,
            "temperature": 0.5,
            "thinkingConfig": {
                "thinkingBudget": 0  # Полное отключение рассуждений для мгновенного старта генерации
            }
        }
    }

    params = {"key": GEMINI_API_KEY}

    try:
        # 4.5 секунды — максимальный порог под 5-секундный лимит Яндекса
        async with httpx.AsyncClient(timeout=4.5) as client:
            resp = await client.post(API_URL, params=params, json=payload, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part and not part.get("thought", False):
                            return part["text"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
                return "Модель прислала пустой результат."
            else:
                error_info = resp.json().get("error", {})
                return f"Ошибка Google API ({resp.status_code}): {error_info.get('message', resp.text)[:200]}"
                
    except httpx.TimeoutException:
        return "Нейросеть не успела ответить за 4.5 секунды. Повторите запрос или задайте вопрос короче."
    except Exception as e:
        return f"Ошибка запроса: {str(e)[:150]}"

@app.post("/webhook")
async def yandex_dialog_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    version = data.get("version", "1.0")
    session = data.get("session", {})
    req_body = data.get("request", {})

    user_text = req_body.get("command", "") or req_body.get("original_utterance", "")
    is_new = session.get("new", False)

    # Мгновенное приветствие при старте без обращения к Gemini
    if is_new or not user_text.strip():
        return {
            "version": version,
            "session": session,
            "response": {
                "text": "Привет! Я подключен к Gemini 3.8 Flash. Задавайте вопрос!",
                "end_session": False
            }
        }

    reply_text = await query_gemini(user_text)

    # Ограничение под лимит одной фразы Алисы (1024 символа)
    if len(reply_text) > 950:
        reply_text = reply_text[:947] + "..."

    return {
        "version": version,
        "session": session,
        "response": {
            "text": reply_text,
            "end_session": False
        }
    }
