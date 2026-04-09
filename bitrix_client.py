import asyncio
import requests
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

BITRIX_API_URL = "https://stalker-co.ru:443/bitrix/tools/mlk_tgbotapi_banner.php"
BITRIX_API_KEY = os.getenv("BITRIX_API_KEY")

def parse_banner(banner: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": banner.get("name"),
        "description": banner.get("description"),
        "image": banner.get("image"),
        "link": banner.get("link"),
        "date_to": banner.get("date_to")
    }

async def get_banners(company_code: str) -> Optional[List[Dict[str, Any]]]:
    if not BITRIX_API_KEY:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None
    params = {
        "key": BITRIX_API_KEY,
        "code": company_code
    }
    try:
        response = await asyncio.to_thread(requests.get, BITRIX_API_URL, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка Bitrix API: статус {response.status_code}")
            return None
        data = response.json()
        banners = data.get("banners", [])
        parsed = [parse_banner(b) for b in banners if b.get("image")]
        return parsed
    except Exception as e:
        logger.error(f"Исключение при запросе к Bitrix API: {e}")
        return None

def get_banners_sync(company_code: str) -> Optional[List[Dict[str, Any]]]:
    if not BITRIX_API_KEY:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None
    params = {
        "key": BITRIX_API_KEY,
        "code": company_code
    }
    try:
        response = requests.get(BITRIX_API_URL, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка Bitrix API: статус {response.status_code}")
            return None
        data = response.json()
        banners = data.get("banners", [])
        parsed = [parse_banner(b) for b in banners if b.get("image")]
        return parsed
    except Exception as e:
        logger.error(f"Исключение при запросе к Bitrix API: {e}")
        return None