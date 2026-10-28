9import os
from fastapi import FastAPI, Request
from google import genai

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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
                "text": "Привет! Я на связи через Gemini. О чем хотите спросить?",
                "end_session": False
            }
        }

    reply_text = "Не удалось получить ответ."
    if client:
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=user_text,
            )
            if response and response.text:
                reply_text = response.text
        except Exception as e:
            reply_text = f"Ошибка Gemini: {str(e)[:200]}"
    else:
        reply_text = "API-ключ не настроен."

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
