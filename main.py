import os
from fastapi import FastAPI, Request
from google import genai

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

@app.post("/webhook")
async def yandex_dialog_webhook(request: Request):
    data = await request.json()

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
                "text": "Привет! Я подключен к Gemini Flash. Какой у вас вопрос?",
                "end_session": False
            }
        }

    reply_text = "Не удалось связаться с нейросетью."
    if client:
        try:
            response = client.interactions.create(
                model="gemini-3.8-flash",
                input=user_text,
                thinking_level="low"
            )
            if response.output:
                reply_text = response.output_text if hasattr(response, "output_text") else str(response.output)
        except Exception as e:
            reply_text = f"Ошибка: {e}"

    if len(reply_text) > 1000:
        reply_text = reply_text[:997] + "..."

    return {
        "version": version,
        "session": session,
        "response": {
            "text": reply_text,
            "end_session": False
        }
    }
