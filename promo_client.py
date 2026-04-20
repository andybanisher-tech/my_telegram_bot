import requests
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PROMO_LIST_URL = "https://exchange.mirlk.ru/SiteExch/hs/site/UrGetPersonalPromotions"
PROMO_DETAIL_URL = "https://stalker-co.ru/bitrix/tools/mlk_tgbotapi_promo.php"

def get_config():
    return {
        "promo_detail_key": os.getenv("PROMO_API_KEY") or os.getenv("BITRIX_API_KEY"),
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
        response = requests.get(PROMO_LIST_URL, params=params, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка API списка акций: статус {response.status_code}")
            return None
        data = response.json()
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

def get_promotion_details_batch_sync(promo_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Загружает детали для нескольких акций одним запросом.
    Возвращает словарь {promo_id: details}.
    """
    config = get_config()
    api_key = config.get("promo_detail_key")
    if not api_key:
        logger.error("PROMO_API_KEY или BITRIX_API_KEY не задан в .env")
        return {}
    if not promo_ids:
        return {}
    # Формируем строку ID через запятую
    ids_string = ','.join(promo_ids)
    params = {
        "key": api_key,
        "promoids": ids_string
    }
    try:
        response = requests.get(PROMO_DETAIL_URL, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Ошибка API деталей акций: статус {response.status_code}")
            return {}
        data = response.json()
        if not isinstance(data, list):
            logger.error(f"Неожиданный формат ответа: {data}")
            return {}
        result = {}
        for item in data:
            promo_id = item.get('id')
            if promo_id:
                result[str(promo_id)] = item
        return result
    except Exception as e:
        logger.error(f"Исключение при запросе деталей акций: {e}")
        return {}

# Старая функция оставлена для обратной совместимости (если используется где-то ещё)
def get_promotion_details_sync(promo_id: str) -> Optional[Dict[str, Any]]:
    result = get_promotion_details_batch_sync([promo_id])
    return result.get(promo_id)