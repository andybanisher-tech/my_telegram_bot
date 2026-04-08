import os
import asyncio
import logging
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from pathlib import Path
import promo_client

# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Акции для вас | Stalker-Co</title>
    <!-- Open Graph мета-теги для красивого превью в Telegram -->
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
            font-size: 18px;
            color: #6c6c70;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007aff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
            color: #000000;
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
        hr {
            margin: 16px 0;
            border: none;
            border-top: 1px solid #e5e5ea;
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
    <script>
        async function loadPromotions() {
            const container = document.getElementById('promo-container');
            const loader = document.getElementById('loader');
            const errorDiv = document.getElementById('error');
            
            const pathParts = window.location.pathname.split('/');
            const partnerCode = pathParts[pathParts.length - 1];
            const url = `/api/promo/${partnerCode}`;
            
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error('Ошибка загрузки');
                const promotions = await response.json();
                loader.style.display = 'none';
                
                if (promotions.length === 0) {
                    container.innerHTML = '<div style="background: white; border-radius: 20px; padding: 40px 20px; text-align: center;">😔 На данный момент для вас нет активных акций</div>';
                    return;
                }
                
                let html = '';
                for (const promo of promotions) {
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
                }
                container.innerHTML = html;
            } catch (err) {
                console.error(err);
                loader.style.display = 'none';
                errorDiv.style.display = 'block';
            }
        }
        
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            }).replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, function(c) {
                return c;
            });
        }
        
        document.addEventListener('DOMContentLoaded', loadPromotions);
    </script>
</head>
<body>
    <div class="container">
        <h1>🎁 Акции для вас</h1>
        <div class="sub">Персональные предложения</div>
        
        <div id="loader" class="loader">
            <div class="spinner"></div>
            Загружаем акции...
        </div>
        <div id="error" style="display: none; text-align: center; color: red; padding: 20px;">
            ⚠️ Не удалось загрузить акции. Попробуйте позже.
        </div>
        <div id="promo-container"></div>
        
        <div class="footer">
            Stalker-Co — всё для профессионалов
        </div>
    </div>
</body>
</html>
"""

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    """Страница с лоадером, данные подгружаются через API"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/promo/<partner_code>')
def api_promo(partner_code):
    """JSON-эндпоинт для получения акций"""
    logger.info(f"API запрос для партнера {partner_code}")
    try:
        promotions_list = run_async(promo_client.get_promotions_list(partner_code))
        logger.info(f"Получено акций из первого запроса: {len(promotions_list) if promotions_list else 0}")
    except Exception as e:
        logger.error(f"Ошибка при получении списка акций: {e}")
        promotions_list = []
    
    if not promotions_list:
        return jsonify([])
    
    enriched_promos = []
    for promo in promotions_list:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
        try:
            details = run_async(promo_client.get_promotion_details(clean_id))
        except Exception as e:
            logger.error(f"Ошибка при получении деталей акции {clean_id}: {e}")
            details = None
        enriched = {
            'name': details.get('name') if details else promo.get('name', 'Акция'),
            'description': details.get('description') if details else '',
            'image': details.get('image') if details else None,
            'link': details.get('link') if details else None,
            'mark': promo.get('mark', ''),
            'date_to': promo.get('date_to', ''),
            'date_from': promo.get('date_from', '')
        }
        enriched_promos.append(enriched)
    
    logger.info(f"Сформировано {len(enriched_promos)} акций для отображения")
    return jsonify(enriched_promos)

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)