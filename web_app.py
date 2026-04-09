import os
import logging
import re
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from pathlib import Path
import promo_client

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'[\ud800-\udfff]', '', text)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Акции для вас | Stalker-Co</title>
    <meta property="og:title" content="🎁 Персональные акции Stalker-Co" />
    <meta property="og:description" content="Акции и специальные предложения, подготовленные специально для вас." />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="https://stalker-co.ru/local/templates/stalker/images/logo.png" />
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            padding: 20px 12px 40px;
            transition: background-color 0.2s, color 0.2s;
        }
        body.light {
            --bg-color: #ffffff;
            --text-color: #1c1c1e;
            --card-bg: #ffffff;
            --border-color: #e5e5ea;
            --meta-color: #6c6c70;
            --brand-bg: #f2f2f7;
            --brand-text: #3a3a3c;
            --button-bg: #007aff;
            --button-hover: #005fc1;
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
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
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
        .promo-title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: var(--text-color); }
        .promo-meta { font-size: 13px; color: var(--meta-color); margin-bottom: 15px; display: flex; align-items: center; gap: 12px; }
        .brand-badge { background-color: var(--brand-bg); padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; color: var(--brand-text); }
        .promo-image { margin: 15px 0; text-align: center; }
        .promo-image img { max-width: 100%; border-radius: 16px; max-height: 240px; object-fit: contain; background: var(--brand-bg); padding: 8px; }
        .promo-description { color: var(--text-color); line-height: 1.45; margin: 15px 0; font-size: 15px; opacity: 0.8; }
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
        .footer { text-align: center; font-size: 12px; color: var(--meta-color); margin-top: 30px; }
        @media (max-width: 480px) { body { padding: 12px; } .promo-card { padding: 16px; } .promo-title { font-size: 18px; } }
    </style>
</head>
<body>
    <div class="container" id="content">
        <h1>🎁 Акции для вас</h1>
        <div class="sub">Персональные предложения</div>
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

        const urlParams = new URLSearchParams(window.location.search);
        const brandFilter = urlParams.get('brand');
        const dataUrl = window.location.pathname + '/data' + (brandFilter ? `?brand=${brandFilter}` : '');
        fetch(dataUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP status ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                const container = document.getElementById('content');
                if (data.promotions && data.promotions.length) {
                    let html = '<h1>🎁 Акции для вас</h1><div class="sub">Персональные предложения</div>';
                    data.promotions.forEach(promo => {
                        html += `
                        <div class="promo-card">
                            <div class="promo-title">${escapeHtml(promo.name)}</div>
                            <div class="promo-meta">
                                ${promo.mark ? `<span class="brand-badge">${escapeHtml(promo.mark)}</span>` : ''}
                                ${promo.date_to ? `<span>📅 до ${escapeHtml(promo.date_to)}</span>` : ''}
                            </div>
                            ${promo.image ? `<div class="promo-image"><img src="${escapeHtml(promo.image)}" alt="Превью акции"></div>` : ''}
                            ${promo.description ? `<div class="promo-description">${escapeHtml(promo.description)}</div>` : ''}
                            ${promo.link ? `<a href="${escapeHtml(promo.link)}" class="promo-button" target="_blank" rel="noopener noreferrer">🔗 Подробнее на сайте</a>` : ''}
                        </div>
                        `;
                    });
                    container.innerHTML = html;
                } else {
                    container.innerHTML = '<h1>🎁 Акции для вас</h1><div class="sub">Персональные предложения</div><div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">😔 На данный момент для вас нет активных акций</div><div class="footer">Stalker-Co — всё для профессионалов</div>';
                }
            })
            .catch(error => {
                console.error('Ошибка загрузки акций:', error);
                document.getElementById('content').innerHTML = '<h1>🎁 Акции для вас</h1><div class="sub">Персональные предложения</div><div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">❌ Ошибка загрузки акций. Попробуйте позже.</div><div class="footer">Stalker-Co — всё для профессионалов</div>';
            });
    </script>
</body>
</html>
"""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE)

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    brand_filter = request.args.get('brand')
    promotions_list = promo_client.get_promotions_list_sync(partner_code)
    if not promotions_list:
        return jsonify({"promotions": []}), 404
    enriched = []
    for promo in promotions_list:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
        details = promo_client.get_promotion_details_sync(clean_id)
        # Фильтруем по бренду, если задан
        if brand_filter:
            promo_mark = promo.get('mark', '')
            if promo_mark.lower() != brand_filter.lower():
                continue
        enriched.append({
            'name': clean_text(details.get('name')) if details else clean_text(promo.get('name', 'Акция')),
            'description': clean_text(details.get('description')) if details else '',
            'image': clean_text(details.get('image')) if details else None,
            'link': clean_text(details.get('link')) if details else None,
            'mark': clean_text(promo.get('mark', '')),
            'date_to': clean_text(promo.get('date_to', ''))
        })
    return jsonify({"promotions": enriched})

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)