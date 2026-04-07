import aiohttp
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PROMO_LIST_URL = "https://exchange.mirlk.ru/SiteExch/hs/site/UrGetPersonalPromotions"
PROMO_DETAIL_URL = "https://dev.stalker-co.ru/bitrix/tools/mlk_tgbotapi_promo.php"
PROMO_DETAIL_KEY = os.getenv("PROMO_API_KEY")
AUTH_KEY = os.getenv("BONUS_API_KEY")  # для авторизации первого запроса
SITE_ID = os.getenv("BONUS_SITE_ID", "113")

async def get_promotions_list(partner_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Получает список акций для партнёра.
    Возвращает список словарей с полями: id, mark, date_from, date_to.
    """
    if not AUTH_KEY:
        logger.error("BONUS_API_KEY не задан в .env")
        return None
    params = {
        "IDPartner": partner_id,
        "SiteID": SITE_ID
    }
    headers = {
        "Authorization": AUTH_KEY,
        "Accept": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PROMO_LIST_URL, params=params, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API списка акций: статус {resp.status}")
                    return None
                data = await resp.json()
                # Ожидаем список объектов с ключами id, mark, date_from, date_to
                if isinstance(data, list):
                    return data
                else:
                    logger.error(f"Неожиданный формат ответа: {data}")
                    return None
    except Exception as e:
        logger.error(f"Исключение при запросе списка акций: {e}")
        return None

async def get_promotion_details(promo_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает детальную информацию об акции по её ID.
    Возвращает словарь с полями: name, description, image, link, date_to и др.
    """
    if not PROMO_DETAIL_KEY:
        logger.error("PROMO_API_KEY не задан в .env")
        return None
    params = {
        "key": PROMO_DETAIL_KEY,
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
        logger.error(f"Исключение при запросе деталей акции {promo_id}: {e}")
        return None