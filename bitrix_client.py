import asyncio
import requests
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

BITRIX_API_URL = "https://stalker-co.ru:443/bitrix/tools/mlk_tgbotapi_banner.php"
BITRIX_API_KEY = os.getenv("BITRIX_API_KEY")

def get_bitrix_config():
    return {
        "api_key": BITRIX_API_KEY,
        "api_url": BITRIX_API_URL
    }

def parse_banner(banner: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": banner.get("name"),
        "description": banner.get("description"),
        "image": banner.get("image"),
        "link": banner.get("link"),
        "date_to": banner.get("date_to")
    }

async def get_banners(company_code: str) -> Optional[List[Dict[str, Any]]]:
    config = get_bitrix_config()
    if not config["api_key"]:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None

    params = {
        "key": config["api_key"],
        "code": company_code
    }
    try:
        response = await asyncio.to_thread(requests.get, config["api_url"], params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка Bitrix API: статус {response.status_code}")
            return None
        data = response.json()
        banners = data.get("banners", [])
        parsed = [parse_banner(b) for b in banners]
        return parsed
    except Exception as e:
        logger.error(f"Исключение при запросе к Bitrix API: {e}")
        return None

# Синхронная версия для использования в Flask
def get_banners_sync(company_code: str) -> Optional[List[Dict[str, Any]]]:
    config = get_bitrix_config()
    if not config["api_key"]:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None

    params = {
        "key": config["api_key"],
        "code": company_code
    }
    try:
        response = requests.get(config["api_url"], params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка Bitrix API: статус {response.status_code}")
            return None
        data = response.json()
        banners = data.get("banners", [])
        parsed = [parse_banner(b) for b in banners]
        return parsed
    except Exception as e:
        logger.error(f"Исключение при запросе к Bitrix API: {e}")
        return None