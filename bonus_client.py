import aiohttp
import ssl
import logging
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

def get_bonus_config():
    """Возвращает конфигурацию бонусного API из переменных окружения."""
    return {
        "api_key": os.getenv("BONUS_API_KEY"),
        "base_url": os.getenv("BONUS_API_BASE", "https://exchange.mirlk.ru/SiteExch/hs/site"),
        "site_id": os.getenv("BONUS_SITE_ID", "113")
    }

async def get_bonus_balance(partner_id: str) -> Optional[Dict[str, Any]]:
    config = get_bonus_config()
    if not config["api_key"]:
        logger.error("BONUS_API_KEY не задан в .env")
        return None
    url = f"{config['base_url']}/UrGetBonusBalance"
    params = {
        "SiteID": config["site_id"],
        "IDPartner": partner_id
    }
    headers = {
        "Authorization": config["api_key"],
        "Accept": "application/json"
    }
    # Создаём SSL-контекст без проверки сертификата
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=30, ssl=ssl_context) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API баланса: статус {resp.status}")
                    return None
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"Исключение при запросе баланса: {e}")
        return None

async def get_bonus_history(partner_id: str) -> Optional[List[Dict[str, Any]]]:
    config = get_bonus_config()
    if not config["api_key"]:
        logger.error("BONUS_API_KEY не задан в .env")
        return None
    url = f"{config['base_url']}/UrGetBonusHistory"
    params = {
        "SiteID": config["site_id"],
        "IDPartner": partner_id
    }
    headers = {
        "Authorization": config["api_key"],
        "Accept": "application/json"
    }
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=30, ssl=ssl_context) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API истории: статус {resp.status}")
                    return None
                data = await resp.json()
                return data.get("lines", [])
    except Exception as e:
        logger.error(f"Исключение при запросе истории: {e}")
        return None