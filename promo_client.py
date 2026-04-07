import aiohttp
import logging
import os
import traceback
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PROMO_LIST_URL = "https://exchange.mirlk.ru/SiteExch/hs/site/UrGetPersonalPromotions"
PROMO_DETAIL_URL = "https://dev.stalker-co.ru/bitrix/tools/mlk_tgbotapi_promo.php"

def get_config():
    return {
        "promo_detail_key": os.getenv("PROMO_API_KEY"),
        "auth_key": os.getenv("BONUS_API_KEY"),
        "site_id": os.getenv("BONUS_SITE_ID", "113")
    }

async def get_promotions_list(partner_id: str) -> Optional[List[Dict[str, Any]]]:
    config = get_config()
    logger.info(f"get_promotions_list called with partner_id={partner_id}")
    logger.info(f"auth_key present: {bool(config['auth_key'])}")
    if not config["auth_key"]:
        logger.error("BONUS_API_KEY не задан в .env")
        return None
    params = {
        "IDPartner": partner_id,
        "SiteID": config["site_id"]
    }
    headers = {
        "Authorization": config["auth_key"],
        "Accept": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PROMO_LIST_URL, params=params, headers=headers, timeout=30) as resp:
                logger.info(f"Response status: {resp.status}")
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Ошибка API списка акций: статус {resp.status}, тело: {text[:500]}")
                    return None
                data = await resp.json()
                logger.info(f"Response data keys: {data.keys() if isinstance(data, dict) else 'list'}")
                if isinstance(data, dict) and "promotions" in data:
                    return data["promotions"]
                elif isinstance(data, list):
                    return data
                else:
                    logger.error(f"Неожиданный формат ответа: {data}")
                    return None
    except Exception as e:
        logger.error(f"Исключение при запросе списка акций: {e}\n{traceback.format_exc()}")
        return None

async def get_promotion_details(promo_id: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("BITRIX_API_KEY")
    if not api_key:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None
    params = {
        "key": api_key,
        "promoid": promo_id
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PROMO_DETAIL_URL, params=params, timeout=30) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API деталей акции {promo_id}: статус {resp.status}")
                    return None
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"Исключение при запросе деталей акции {promo_id}: {e}\n{traceback.format_exc()}")
        return None