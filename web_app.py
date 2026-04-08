import os
from flask import Flask, render_template_string, abort
import promo_client  # Импортируем вашу существующую логику
import asyncio

app = Flask(__name__)

# Шаблон HTML-страницы
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
</head>
<body>
    <div class="container">
        <h1>🎁 Акции для вас</h1>
        <div class="sub">Персональные предложения</div>

        {% if promotions %}
            {% for promo in promotions %}
            <div class="promo-card">
                <div class="promo-title">{{ promo.name | e }}</div>
                <div class="promo-meta">
                    {% if promo.mark %}
                    <span class="brand-badge">{{ promo.mark | e }}</span>
                    {% endif %}
                    {% if promo.date_to %}
                    <span>📅 до {{ promo.date_to }}</span>
                    {% endif %}
                </div>
                {% if promo.image %}
                <div class="promo-image">
                    <img src="{{ promo.image }}" alt="Превью акции {{ promo.name | e }}">
                </div>
                {% endif %}
                {% if promo.description %}
                <div class="promo-description">{{ promo.description | e }}</div>
                {% endif %}
                {% if promo.link %}
                <a href="{{ promo.link }}" class="promo-button" target="_blank" rel="noopener noreferrer">
                    🔗 Подробнее на сайте
                </a>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div style="background: white; border-radius: 20px; padding: 40px 20px; text-align: center;">
                😔 На данный момент для вас нет активных акций
            </div>
        {% endif %}
        <div class="footer">
            Stalker-Co — всё для профессионалов
        </div>
    </div>
</body>
</html>
"""

def run_async(coro):
    """Вспомогательная функция для запуска асинхронного кода из синхронного Flask"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    """
    Генерирует HTML-страницу с акциями для указанного партнера.
    Пример URL: https://your-domain.com/promo/С88201
    """
    # Получаем список акций через вашу существующую функцию
    promotions_list = run_async(promo_client.get_promotions_list(partner_code))
    
    if not promotions_list:
        # Если акций нет, показываем страницу-заглушку
        return render_template_string(HTML_TEMPLATE, promotions=[]), 404

    enriched_promos = []
    for promo in promotions_list:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        
        # Очищаем ID от ведущих нулей
        clean_id = str(int(promo_id)) if promo_id.isdigit() else promo_id
        
        # Пытаемся получить детали
        details = run_async(promo_client.get_promotion_details(clean_id))
        
        # Собираем итоговый словарь: приоритет у деталей из второго запроса
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

    return render_template_string(HTML_TEMPLATE, promotions=enriched_promos)

@app.route('/health')
def health_check():
    """Эндпоинт для проверки работоспособности сервера"""
    return "OK", 200

if __name__ == '__main__':
    # Для локальной отладки
    app.run(host='0.0.0.0', port=8000)