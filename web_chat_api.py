import logging
from pathlib import Path
from dotenv import load_dotenv

# ВАЖНО: грузим .env до импорта web_chat_handler / promo_client —
# иначе BONUS_API_KEY, BITRIX_API_KEY и др. будут None, и акции/баланс
# вернут «нет данных» (см. promo_client.get_config).
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

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
    partner_id: str = None   # для акций
    no_products: int = 0     # 1 = фронт сам подгрузит карточки, не дублируй

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    reply = await handle_web_message(
        user_id=req.user_id,
        message_text=req.message,
        context=req.context,
        partner_id=req.partner_id,
        no_products=bool(req.no_products),
    )
    return {"response": reply}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)