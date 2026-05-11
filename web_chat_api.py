import sys
import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Добавим путь к нашему боту, чтобы импортировать его модули
sys.path.append(os.path.dirname(__file__))

# Импортируем необходимые функции из вашего бота
from bot import dp, bot, LLM_SERVER_URL, LLM_MODEL
from handlers.chat import generate_response  # предполагается, что у вас там функция для генерации ответа
from handlers.start import search_user  # функция поиска пользователя по номеру
from handlers.commands import send_llm_request  # функция отправки запроса к LLM

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    phone: str = None  # если есть возможность получить телефон
    message: str
    context: str = ""  # контекст из поиска

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # Получаем данные пользователя по телефону (если передан)
        user_data = None
        if req.phone:
            user_data = await search_user(req.phone)
            if not user_data:
                return {"response": "Пользователь с таким номером не найден."}
        # Иначе можно попробовать найти по user_id (если есть соответствующий API)
        # Формируем промпт для LLM с учётом контекста
        prompt = f"Клиент {user_data.get('name', '')} (группа {user_data.get('group', '')}). " if user_data else ""
        prompt += f"Контекст поиска: {req.context}. " if req.context else ""
        prompt += f"Сообщение: {req.message}"
        
        response = await generate_response(prompt)  # функция генерации ответа из вашего бота
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
    