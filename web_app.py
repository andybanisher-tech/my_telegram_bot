import os
import logging
import re
from flask import Flask, render_template_string, jsonify
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import promo_client

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
    <!-- Open Graph мета-теги -->
    <meta property="og:title" content="🎁 Персональные акции Stalker-Co" />
    <meta property="og:description" content="Акции и специальные предложения, подготовленные специально для вас." />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="https://stalker-co.ru/local/templates/stalker/images/logo.png" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f2f2f7;
            padding: 20px 12px 40px;
            color: #1c1c1e;
            transition: background-color 0.3s, color 0.2s;
        }
        /* Тёмная тема */
        @media (prefers-color-scheme: dark) {
            body {
                background-color: #000000;
                color: #ffffff;
            }
            .promo-card {
                background-color: #1c1c1e;
                border-color: #2c2c2e;
            }
            .brand-badge {
                background-color: #2c2c2e;
                color: #e5e5ea;
            }
            .promo-meta {
                color: #8e8e93;
            }
            .promo-description {
                color: #e5e5ea;
            }
            .footer {
                color: #6c6c70;
            }
        }
        .container {
            max-width: 550px;
            margin: 0 auto;
        }
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
            text-align: center;
            color: inherit;
        }
        .sub {
            text-align: center;
            color: #6c6c70;
            margin-bottom: 28px;
            font-size: 15px;
        }
        .loader {
            text-align: center;
            padding: 40px;
            color: #6c6c70;
        }
        .promo-card {
            background: white;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.1s ease;
            border: 1px solid #e5e5ea;
        }
        .promo-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        }
        .promo-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: inherit;
            line-height: 1.3;
        }
        .promo-meta {
            font-size: 13px;
            color: #8e8e93;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-badge {
            background-color: #f2f2f7;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 12px;
            color: #3a3a3c;
        }
        .promo-image {
            margin: 15px 0;
            text-align: center;
        }
        .promo-image img {
            max-width: 100%;
            border-radius: 16px;
            max-height: 240px;
            object-fit: contain;
            background: #f9f9fb;
            padding: 8px;
        }
        .promo-description {
            color: #3a3a3c;
            line-height: 1.45;
            margin: 15px 0;
            font-size: 15px;
        }
        .promo-button {
            display: inline-block;
            background-color: #007aff;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 14px;
            font-weight: 500;
            margin-top: 12px;
            transition: background 0.2s;
            text-align: center;
            width: 100%;
            box-sizing: border-box;
        }
        .promo-button:hover {
            background-color: #005fc1;
        }
        .footer {
            text-align: center;
            font-size: 12px;
            color: #8e8e93;
            margin-top: 30px;
        }
        @media (max-width: 480px) {
            body { padding: 12px; }
            .promo-card { padding: 16px; }
            .promo-title { font-size: 18px; }
        }
    </style>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        document.addEventListener('DOMContentLoaded', function() {
            fetch(window.location.href + '/data')
                .then(response => response.json())
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
                        container.innerHTML = '<h1>🎁 Акции для вас</h1><div class="sub">Персональные предложения</div><div style="background: white; border-radius: 20px; padding: 40px 20px; text-align: center;">😔 На данный момент для вас нет активных акций</div><div class="footer">Stalker-Co — всё для профессионалов</div>';
                    }
                })
                .catch(error => {
                    console.error('Ошибка загрузки акций:', error);
                    document.getElementById('content').innerHTML = '<h1>🎁 Акции для вас</h1><div class="sub">Персональные предложения</div><div style="background: white; border-radius: 20px; padding: 40px 20px; text-align: center;">❌ Ошибка загрузки акций. Попробуйте позже.</div><div class="footer">Stalker-Co — всё для профессионалов</div>';
                });
        });
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            });
        }
    </script>
</head>
<body>
    <div class="container" id="content">
        <h1>🎁 Акции для вас</h1>
        <div class="sub">Персональные предложения</div>
        <div class="loader">⏳ Загружаем акции...</div>
    </div>
    <div class="footer">
        Stalker-Co 
    </div>
</body>
</html>
"""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE)

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    logger.info(f"Запрос данных для партнера {partner_code}")
    try:
        promotions_list = promo_client.get_promotions_list_sync(partner_code)
    except Exception as e:
        logger.error(f"Ошибка при получении списка акций: {e}")
        promotions_list = None

    if not promotions_list:
        return jsonify({"promotions": []}), 404

    enriched = []
    for promo in promotions_list:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
        try:
            details = promo_client.get_promotion_details_sync(clean_id)
        except Exception as e:
            logger.error(f"Ошибка при получении деталей акции {clean_id}: {e}")
            details = None
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