import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"

async def query_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Не указан GEMINI_API_KEY в настройках."

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 150,
            "temperature": 0.4,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }
    params = {"key": GEMINI_API_KEY}

    try:
        # Лимит 3.0 сек гарантирует ответ до разрыва соединения Яндексом
        async with httpx.AsyncClient(timeout=3.0) as client:
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
                return "Модель прислала пустой ответ."
            
            if resp.status_code == 503:
                return "Серверы перегружены. Повторите запрос через секунду."
                
            err = resp.json().get("error", {}).get("message", resp.text)
            return f"Ошибка API ({resp.status_code}): {err[:150]}"
            
    except httpx.TimeoutException:
        return "Нейросеть долго думает. Попробуйте задать вопрос короче."
    except Exception as e:
        return f"Сетевая ошибка: {str(e)[:100]}"

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

    if is_new or not user_text.strip():
        return {
            "version": version,
            "session": session,
            "response": {
                "text": "Привет! Я подключен к Gemini 3.8 Flash. Какой у вас вопрос?",
                "end_session": False
            }
        }

    reply_text = await query_gemini(user_text)

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
