import os
import re
import logging
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import promo_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    if not text:
        return ""
    # Удаляем суррогатные пары UTF-16
    return re.sub(r'[\ud800-\udfff]', '', text)

# HTML-шаблон с лоадером и динамической подгрузкой данных
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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f2f2f7;
            padding: 20px 12px 40px;
            color: #1c1c1e;
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
            color: #000000;
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
            border: 1px solid #e5e5ea;
        }
        .promo-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #000000;
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
    </style>
    <script>
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            });
        }
        fetch('/promo/{{ partner_code }}/data')
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
    </script>
</head>
<body>
    <div class="container" id="content">
        <h1>🎁 Акции для вас</h1>
        <div class="sub">Персональные предложения</div>
        <div class="loader">⏳ Загружаем акции...</div>
    </div>
</body>
</html>
"""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE, partner_code=partner_code)

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    logger.info(f"Запрос данных для партнера {partner_code}")
    promotions = promo_client.get_promotions_list_sync(partner_code)
    if not promotions:
        logger.info(f"Акции не найдены для {partner_code}")
        return jsonify({"promotions": []})

    enriched = []
    for promo in promotions:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        # Очищаем ID от ведущих нулей
        clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
        details = promo_client.get_promotion_details_sync(clean_id)
        enriched.append({
            'name': clean_text(details.get('name')) if details else clean_text(promo.get('name', 'Акция')),
            'description': clean_text(details.get('description')) if details else '',
            'image': clean_text(details.get('image')) if details else None,
            'link': clean_text(details.get('link')) if details else None,
            'mark': clean_text(promo.get('mark', '')),
            'date_to': clean_text(promo.get('date_to', ''))
        })
    logger.info(f"Сформировано {len(enriched)} акций для отображения")
    return jsonify({"promotions": enriched})

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)