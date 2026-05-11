import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from web_chat_handler import handle_web_message

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: int = 0
    message: str
    context: str = ""

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    reply = await handle_web_message(
        user_id=req.user_id,
        message_text=req.message,
        context=req.context
    )
    return {"response": reply}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)