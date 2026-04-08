import os
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PROMO_LIST_URL = "https://exchange.mirlk.ru/SiteExch/hs/site/UrGetPersonalPromotions"
PROMO_DETAIL_URL = "https://stalker-co.ru/bitrix/tools/mlk_tgbotapi_promo.php"

def get_config():
    return {
        "promo_detail_key": os.getenv("BITRIX_API_KEY"),  # используем BITRIX_API_KEY для второго запроса
        "auth_key": os.getenv("BONUS_API_KEY"),
        "site_id": os.getenv("BONUS_SITE_ID", "113")
    }

def get_promotions_list_sync(partner_id: str) -> Optional[List[Dict[str, Any]]]:
    config = get_config()
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
        resp = requests.get(PROMO_LIST_URL, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Ошибка API списка акций: статус {resp.status_code}")
            return None
        data = resp.json()
        if isinstance(data, dict) and "promotions" in data:
            return data["promotions"]
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Неожиданный формат ответа: {data}")
            return None
    except Exception as e:
        logger.error(f"Исключение при запросе списка акций: {e}")
        return None

def get_promotion_details_sync(promo_id: str) -> Optional[Dict[str, Any]]:
    config = get_config()
    api_key = config.get("promo_detail_key")
    if not api_key:
        logger.error("BITRIX_API_KEY не задан в .env")
        return None
    params = {
        "key": api_key,
        "promoid": promo_id
    }
    try:
        resp = requests.get(PROMO_DETAIL_URL, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Ошибка API деталей акции {promo_id}: статус {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"Исключение при запросе деталей акции {promo_id}: {e}")
        return None