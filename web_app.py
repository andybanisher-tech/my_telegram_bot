from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/promo/<partner_code>/data')
def promo_data(partner_code):
    # Возвращаем тестовые акции
    return jsonify({
        "promotions": [
            {"name": "Тестовая акция", "mark": "Test", "date_to": "31.12.2026", "image": None, "link": None}
        ]
    })

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return """<!DOCTYPE html>
    <html>
    <body>
        <h1>Акции</h1>
        <div id="content">Загрузка...</div>
        <script>
            fetch('/promo/С88201/data')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('content').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
        </script>
    </body>
    </html>"""