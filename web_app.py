import os
import logging
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from pathlib import Path
import promo_client
import bitrix_client
from functools import lru_cache

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'[\ud800-\udfff]', '', text)

HTML_TEMPLATE = """... (ваш существующий шаблон) ..."""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE)

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    all_mode = request.args.get('all') == '1'
    brand_filter = request.args.get('brand')
    if all_mode:
        banners = bitrix_client.get_banners_sync(partner_code)
        if not banners:
            return jsonify({"promotions": []}), 404
        enriched = []
        for banner in banners:
            enriched.append({
                'name': clean_text(banner.get('name', 'Акция')),
                'description': clean_text(banner.get('description', '')),
                'image': clean_text(banner.get('image')),
                'link': clean_text(banner.get('link')),
                'mark': '',
                'date_to': clean_text(banner.get('date_to', ''))
            })
        if brand_filter:
            enriched = [p for p in enriched if brand_filter.lower() in p['name'].lower()]
        return jsonify({"promotions": enriched})
    else:
        promotions_list = promo_client.get_promotions_list_sync(partner_code)
        if not promotions_list:
            return jsonify({"promotions": []}), 404
        
        # Параллельная загрузка деталей
        enriched = [None] * len(promotions_list)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_idx = {}
            for idx, promo in enumerate(promotions_list):
                promo_id = promo.get('id')
                if not promo_id:
                    continue
                clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
                future = executor.submit(promo_client.get_promotion_details_sync, clean_id)
                future_to_idx[future] = idx
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                promo = promotions_list[idx]
                try:
                    details = future.result()
                except Exception as e:
                    logger.error(f"Ошибка загрузки деталей для {promo.get('id')}: {e}")
                    details = None
                if brand_filter:
                    promo_mark = promo.get('mark', '')
                    if promo_mark.lower() != brand_filter.lower():
                        continue
                enriched[idx] = {
                    'name': clean_text(details.get('name')) if details else clean_text(promo.get('name', 'Акция')),
                    'description': clean_text(details.get('description')) if details else '',
                    'image': clean_text(details.get('image')) if details else None,
                    'link': clean_text(details.get('link')) if details else None,
                    'mark': clean_text(promo.get('mark', '')),
                    'date_to': clean_text(promo.get('date_to', ''))
                }
        enriched = [e for e in enriched if e is not None]
        return jsonify({"promotions": enriched})

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)