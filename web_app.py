import os
import logging
import re
import urllib.parse
from flask import Flask, render_template_string, jsonify, request, redirect, abort
from dotenv import load_dotenv
from pathlib import Path

import promo_client
import bitrix_client
import database as db

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'[\ud800-\udfff]', '', text)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Акции для вас | Stalker-Co</title>
    <meta property="og:title" content="� Персональные акции Stalker-Co" />
    <meta property="og:description" content="Акции и специальные предложения, подготовленные специально для вас." />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="https://stalker-co.ru/local/templates/stalker/images/logo.png" />
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 20px 12px 40px;
            transition: background-color 0.2s, color 0.2s;
        }
        body.light {
            --bg-color: #f2f2f7;
            --text-color: #1c1c1e;
            --card-bg: #ffffff;
            --border-color: #e5e5ea;
            --meta-color: #6c6c70;
            --brand-bg: #f2f2f7;
            --brand-text: #3a3a3c;
            --button-bg: #007aff;
            --button-hover: #005fc1;
            --warning-bg: #fff3cd;
            --warning-border: #ffeeba;
            --warning-text: #856404;
        }
        body.dark {
            --bg-color: #000000;
            --text-color: #ffffff;
            --card-bg: #1c1c1e;
            --border-color: #2c2c2e;
            --meta-color: #8e8e93;
            --brand-bg: #2c2c2e;
            --brand-text: #e5e5ea;
            --button-bg: #0a84ff;
            --button-hover: #005fc1;
            --warning-bg: #332e00;
            --warning-border: #665c00;
            --warning-text: #ffea8f;
        }
        .container { max-width: 550px; margin: 0 auto; }
        h1 { font-size: 28px; font-weight: 600; margin-bottom: 8px; text-align: center; color: var(--text-color); }
        .sub { text-align: center; color: var(--meta-color); margin-bottom: 28px; font-size: 15px; }
        .loader { text-align: center; padding: 40px; color: var(--meta-color); }
        .promo-card {
            background: var(--card-bg);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid var(--border-color);
        }
        .promo-card.warning {
            background: var(--warning-bg);
            border-color: var(--warning-border);
        }
        .promo-title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: var(--text-color); }
        .promo-meta { font-size: 13px; color: var(--meta-color); margin-bottom: 15px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .brand-badge { background-color: var(--brand-bg); padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; color: var(--brand-text); }
        .promo-id {
            font-family: monospace;
            background: var(--brand-bg);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            color: var(--brand-text);
        }
        .promo-image { margin: 15px 0; text-align: center; }
        .promo-image img { max-width: 100%; border-radius: 16px; max-height: 240px; object-fit: contain; background: var(--brand-bg); padding: 8px; }
        .promo-description { line-height: 1.45; margin: 15px 0; font-size: 15px; color: var(--text-color); opacity: 0.8; }
        .promo-button {
            display: inline-block;
            background-color: var(--button-bg);
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 14px;
            font-weight: 500;
            margin-top: 12px;
            text-align: center;
            width: 100%;
            box-sizing: border-box;
            transition: background 0.2s;
        }
        .promo-button:hover { background-color: var(--button-hover); }
        .warning-text {
            color: var(--warning-text);
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
            text-align: center;
        }
        .footer { text-align: center; font-size: 12px; color: var(--meta-color); margin-top: 30px; }
        @media (max-width: 480px) { body { padding: 12px; } .promo-card { padding: 16px; } .promo-title { font-size: 18px; } }
    </style>
</head>
<body>
    <div class="container" id="content">
        <h1 id="main-title">� Акции для вас</h1>
        <div class="sub" id="sub-title">Персональные предложения</div>
        <div class="loader">⏳ Загружаем акции...</div>
    </div>
    <div class="footer">Stalker-Co — всё для профессионалов</div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();

        function setTheme() {
            if (tg.colorScheme === 'dark') {
                document.body.classList.add('dark');
                document.body.classList.remove('light');
            } else {
                document.body.classList.add('light');
                document.body.classList.remove('dark');
            }
        }
        setTheme();
        tg.onEvent('themeChanged', setTheme);

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            });
        }

        function trackClick(promoId, promoName, originalUrl) {
            fetch('/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    promo_id: promoId,
                    promo_name: promoName,
                    user_id: tg.initDataUnsafe?.user?.id
                })
            }).finally(() => {
                window.location.href = originalUrl;
            });
            return false;
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            return dateStr.split(' ')[0];
        }

        const urlParams = new URLSearchParams(window.location.search);
        const brandFilter = urlParams.get('brand');
        const allMode = urlParams.get('all') === '1';
        const debugMode = urlParams.get('debug') === '1';
        let partnerName = urlParams.get('name');
        let partnerId = window.location.pathname.split('/').pop();

        if (partnerId) {
            try { partnerId = decodeURIComponent(partnerId); } catch(e) {}
        }
        if (partnerName) {
            try { partnerName = decodeURIComponent(partnerName); } catch(e) {}
        }

        let pageTitle = '� Акции для вас';
        let pageSubtitle = 'Персональные предложения';
        if (partnerName) {
            pageTitle = `� Акции для ${escapeHtml(partnerName)}`;
            pageSubtitle = `Персональные предложения (ID: ${escapeHtml(partnerId)})`;
        } else if (allMode) {
            pageTitle = '� Все акции сайта';
            pageSubtitle = 'Актуальные предложения';
        } else if (debugMode) {
            pageTitle = '� Технический режим: проверка акций';
            pageSubtitle = 'Жёлтым выделены акции без описания на сайте';
        }

        document.getElementById('main-title').innerText = pageTitle;
        document.getElementById('sub-title').innerText = pageSubtitle;

        let dataUrl = window.location.pathname + '/data' + (brandFilter ? `?brand=${brandFilter}` : '');
        if (debugMode) dataUrl += (brandFilter ? '&' : '?') + 'debug=1';
        else if (allMode) dataUrl += (brandFilter ? '&' : '?') + 'all=1';

        fetch(dataUrl)
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('content');
                if (data.promotions && data.promotions.length) {
                    let html = `<h1>${escapeHtml(pageTitle)}</h1><div class="sub">${escapeHtml(pageSubtitle)}</div>`;
                    data.promotions.forEach(promo => {
                        const cardClass = promo.details_missing ? 'promo-card warning' : 'promo-card';
                        const promoLink = promo.link && !promo.details_missing ? `/click?promo_id=${encodeURIComponent(promo.id)}&promo_name=${encodeURIComponent(promo.name)}&url=${encodeURIComponent(promo.link)}` : null;
                        const promoIdHtml = debugMode ? `<span class="promo-id">ID: ${escapeHtml(promo.id)}</span>` : '';
                        html += `
                        <div class="${cardClass}">
                            <div class="promo-title">${escapeHtml(promo.name)}</div>
                            <div class="promo-meta">
                                ${promo.mark ? `<span class="brand-badge">${escapeHtml(promo.mark)}</span>` : ''}
                                ${promoIdHtml}
                                ${promo.date_to ? `<span>� до ${formatDate(promo.date_to)}</span>` : ''}
                            </div>
                            ${promo.image ? `<div class="promo-image"><img src="${escapeHtml(promo.image)}" alt="Превью акции"></div>` : ''}
                            ${promo.description ? `<div class="promo-description">${escapeHtml(promo.description)}</div>` : ''}
                            ${promo.details_missing ? `<div class="warning-text">⚠️ ВНИМАНИЕ: Для этой акции нет описания на сайте! Требуется настройка.</div>` : ''}
                            ${promoLink ? `<a href="#" onclick="trackClick('${escapeHtml(promo.id)}', '${escapeHtml(promo.name)}', '${escapeHtml(promo.link)}'); return false;" class="promo-button">� Подробнее на сайте</a>` : ''}
                        </div>
                        `;
                    });
                    container.innerHTML = html;
                } else {
                    container.innerHTML = `<h1>${escapeHtml(pageTitle)}</h1><div class="sub">${escapeHtml(pageSubtitle)}</div><div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">� На данный момент нет активных акций</div><div class="footer">Stalker-Co — всё для профессионалов</div>`;
                }
            })
            .catch(error => {
                console.error('Ошибка загрузки акций:', error);
                document.getElementById('content').innerHTML = `<h1>${escapeHtml(pageTitle)}</h1><div class="sub">${escapeHtml(pageSubtitle)}</div><div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">❌ Ошибка загрузки акций. Попробуйте позже.</div><div class="footer">Stalker-Co — всё для профессионалов</div>`;
            });
    </script>
</body>
</html>
"""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE)

@app.route('/click', methods=['GET', 'POST'])
def click_handler():
    if request.method == 'GET':
        promo_id = request.args.get('promo_id')
        promo_name = request.args.get('promo_name')
        target_url = request.args.get('url')
        user_id = request.args.get('user_id')
        if promo_id and promo_name and target_url:
            if user_id and user_id.isdigit():
                db.log_promo_click(int(user_id), promo_id, promo_name)
            else:
                db.log_promo_click(None, promo_id, promo_name)
            return redirect(target_url)
        else:
            return abort(400, "Missing parameters")
    elif request.method == 'POST':
        data = request.get_json()
        promo_id = data.get('promo_id')
        promo_name = data.get('promo_name')
        user_id = data.get('user_id')
        target_url = data.get('url')
        if not target_url:
            return jsonify({"error": "Missing url"}), 400
        if promo_id and promo_name:
            if user_id:
                db.log_promo_click(user_id, promo_id, promo_name)
            else:
                db.log_promo_click(None, promo_id, promo_name)
        return jsonify({"status": "ok"})

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    debug_mode = request.args.get('debug') == '1'
    all_mode = request.args.get('all') == '1'
    brand_filter = request.args.get('brand')

    logger.info(f"Запрос данных: partner={partner_code}, debug={debug_mode}, all={all_mode}, brand={brand_filter}")

    # 1. Технический режим: показываем все акции из первого запроса, помечая отсутствие деталей
    if debug_mode:
        promotions_list = promo_client.get_promotions_list_sync(partner_code)
        if not promotions_list:
            return jsonify({"promotions": []}), 404

        promo_ids = []
        promo_map = {}
        for promo in promotions_list:
            promo_id = promo.get('id')
            if promo_id:
                promo_ids.append(promo_id)
                promo_map[promo_id] = promo

        details_map = promo_client.get_promotion_details_batch_sync(promo_ids) if promo_ids else {}

        enriched = []
        for promo_id, promo in promo_map.items():
            details = details_map.get(promo_id)
            enriched.append({
                'id': promo_id,
                'name': clean_text(promo.get('name', 'Акция')),
                'description': clean_text(details.get('description')) if details else '',
                'image': clean_text(details.get('image')) if details else None,
                'link': clean_text(details.get('link')) if details else None,
                'mark': clean_text(promo.get('mark', '')),
                'date_to': clean_text(promo.get('date_to', '')),
                'details_missing': details is None
            })
        if brand_filter:
            enriched = [p for p in enriched if brand_filter.lower() in p['name'].lower()]
        return jsonify({"promotions": enriched})

    # 2. Режим all=1: показываем все акции из второго запроса (banners)
    if all_mode:
        banners = bitrix_client.get_banners_sync(partner_code)
        if not banners:
            return jsonify({"promotions": []}), 404
        enriched = []
        for banner in banners:
            enriched.append({
                'id': banner.get('id'),
                'name': clean_text(banner.get('name', 'Акция')),
                'description': clean_text(banner.get('description', '')),
                'image': clean_text(banner.get('image')),
                'link': clean_text(banner.get('link')),
                'mark': '',
                'date_to': clean_text(banner.get('date_to', '')),
                'details_missing': False
            })
        if brand_filter:
            enriched = [p for p in enriched if brand_filter.lower() in p['name'].lower()]
        return jsonify({"promotions": enriched})

    # 3. Обычный режим: персональные акции, только те, для которых есть детали
    promotions_list = promo_client.get_promotions_list_sync(partner_code)
    if not promotions_list:
        return jsonify({"promotions": []}), 404

    promo_ids = []
    promo_map = {}
    for promo in promotions_list:
        promo_id = promo.get('id')
        if promo_id:
            promo_ids.append(promo_id)
            promo_map[promo_id] = promo

    if not promo_ids:
        return jsonify({"promotions": []}), 404

    details_map = promo_client.get_promotion_details_batch_sync(promo_ids)

    enriched = []
    for promo_id, promo in promo_map.items():
        details = details_map.get(promo_id)
        if not details:
            continue
        if brand_filter:
            promo_mark = promo.get('mark', '')
            if promo_mark.lower() != brand_filter.lower():
                continue
        enriched.append({
            'id': promo_id,
            'name': clean_text(details.get('name')) if details else clean_text(promo.get('name', 'Акция')),
            'description': clean_text(details.get('description')) if details else '',
            'image': clean_text(details.get('image')) if details else None,
            'link': clean_text(details.get('link')) if details else None,
            'mark': clean_text(promo.get('mark', '')),
            'date_to': clean_text(promo.get('date_to', '')),
            'details_missing': False
        })
    return jsonify({"promotions": enriched})

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)