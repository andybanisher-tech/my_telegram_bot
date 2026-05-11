import sys
import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Разрешаем CORS для всех источников (или укажите ваш домен)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_SERVER_URL = "http://31.76.227.1:8000/v1/chat/completions"
LLM_MODEL = "cotype-nano-Q4_K_M.gguf"

class ChatRequest(BaseModel):
    user_id: str
    message: str
    context: str = ""

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        prompt = f"Клиент (ID {req.user_id}). Контекст: {req.context}. Сообщение: {req.message}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                LLM_SERVER_URL,
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 200
                },
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"LLM error: {resp.status_code}")
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
        return {"response": answer.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)