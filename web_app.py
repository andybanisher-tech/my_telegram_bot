import os
import logging
import re
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
    <title>Акции | Stalker-Co</title>
    <meta property="og:title" content="Акции Stalker-Co" />
    <meta property="og:description" content="Актуальные акции и предложения." />
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
        body.light {
            --site-only-bg: #e8f4fd;
            --site-only-border: #b3d9f5;
            --site-only-text: #0a5c8a;
            --segment-bg: #fff0e0;
            --segment-border: #ffd5a0;
            --segment-text: #7a4000;
            --hidden-bg: #f0f0f0;
            --hidden-border: #d0d0d0;
            --hidden-text: #666666;
        }
        body.dark {
            --site-only-bg: #0a2a3d;
            --site-only-border: #0f4a6e;
            --site-only-text: #7dc8f5;
            --segment-bg: #2d1a00;
            --segment-border: #5a3500;
            --segment-text: #ffb060;
            --hidden-bg: #1a1a1a;
            --hidden-border: #333333;
            --hidden-text: #888888;
        }
        .promo-card.site-only {
            background: var(--site-only-bg);
            border-color: var(--site-only-border);
        }
        .promo-card.segment-blocked {
            background: var(--segment-bg);
            border-color: var(--segment-border);
        }
        .promo-card.hidden-card {
            background: var(--hidden-bg);
            border-color: var(--hidden-border);
            opacity: 0.7;
        }
        .debug-label {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 10px;
            margin-bottom: 8px;
            letter-spacing: 0.3px;
        }
        .label-shown { background: #34c759; color: white; }
        .label-site-only { background: var(--site-only-text); color: white; }
        .label-segment-blocked { background: var(--segment-text); color: white; }
        .label-no-site { background: #ff9500; color: white; }
        .label-hidden { background: var(--hidden-text); color: white; }
        .debug-meta { font-size: 12px; margin-top: 8px; opacity: 0.7; font-family: monospace; }
        .debug-section-header {
            font-size: 13px;
            font-weight: 600;
            color: var(--meta-color);
            margin: 20px 0 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        /* ── Debug filters ── */
        .debug-filters {
            position: sticky;
            top: 0;
            z-index: 20;
            background: var(--bg-color);
            padding: 10px 12px 12px;
            margin: -20px -12px 16px;
            border-bottom: 1px solid var(--border-color);
        }
        .filter-search {
            width: 100%;
            padding: 9px 13px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            font-size: 14px;
            margin-bottom: 8px;
            outline: none;
        }
        .filter-search:focus { border-color: var(--button-bg); }
        .filter-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .filter-select {
            padding: 6px 10px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            color: var(--text-color);
            font-size: 13px;
            flex: 1;
            min-width: 110px;
            outline: none;
        }
        .filter-count { font-size: 12px; color: var(--meta-color); white-space: nowrap; margin-left: auto; }
        .status-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
        .status-chip {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 600;
            cursor: pointer; user-select: none; white-space: nowrap;
            border: 2px solid transparent;
            transition: opacity 0.15s, border-color 0.15s;
        }
        .status-chip.off { opacity: 0.3; }
        .status-chip.on { border-color: rgba(255,255,255,0.5); }
        .chip-count { font-size: 10px; opacity: 0.85; }
        .filter-reset {
            font-size: 12px; color: var(--button-bg); cursor: pointer;
            padding: 4px 0; text-decoration: underline; white-space: nowrap;
        }
        .footer { text-align: center; font-size: 12px; color: var(--meta-color); margin-top: 30px; }
        @media (max-width: 480px) { body { padding: 12px; } .promo-card { padding: 16px; } .promo-title { font-size: 18px; } }
    </style>
</head>
<body>
    <div id="debug-filters" class="debug-filters" style="display:none">
        <div style="max-width:550px;margin:0 auto">
            <input type="text" id="filter-search" class="filter-search" placeholder="ID акции, название, ID сегмента…">
            <div class="filter-row">
                <select id="filter-brand" class="filter-select"><option value="">Все марки</option></select>
                <span id="filter-count" class="filter-count"></span>
                <span class="filter-reset" id="filter-reset">Сбросить</span>
            </div>
            <div class="status-chips" id="status-chips"></div>
        </div>
    </div>
    <div class="container" id="content"></div>
    <div class="footer">Stalker-Co — всё для профессионалов</div>
    <script>
        // Внутри Telegram используем настоящий WebApp, вне его (обычный браузер,
        // напр. для debug-режима) — безопасную заглушку, чтобы скрипт не падал,
        // если telegram-web-app.js недоступен или window.Telegram отсутствует.
        const tg = (window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : {
            ready: function() {},
            onEvent: function() {},
            openLink: function(url) { window.open(url, '_blank'); },
            colorScheme: (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light',
            initDataUnsafe: {}
        };
        try { tg.ready(); } catch (e) {}

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
        try { tg.onEvent('themeChanged', setTheme); } catch (e) {}

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
            }).catch(e => console.error('Click log error:', e));
            tg.openLink(originalUrl);
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

        let dataUrl = window.location.pathname + '/data' + (brandFilter ? `?brand=${brandFilter}` : '');
        if (debugMode) dataUrl += (brandFilter ? '&' : '?') + 'debug=1';
        else if (allMode) dataUrl += (brandFilter ? '&' : '?') + 'all=1';

        const STATUS_META = {
            'shown':           { label: 'label-shown',           text: '✅ Показывается',                      chip: 'Показывается',          card: 'promo-card' },
            'site_only':       { label: 'label-site-only',       text: '🌐 Есть на сайте, нет в 1С', chip: 'Только на сайте',       card: 'promo-card site-only' },
            'segment_blocked': { label: 'label-segment-blocked', text: '🔒 Заблокирована сегментом',            chip: 'Блок по сегменту',      card: 'promo-card segment-blocked' },
            'no_site':         { label: 'label-no-site',         text: '⚠️ Есть в 1С, нет на сайте', chip: 'Только в личном списке', card: 'promo-card warning' },
            'hidden':          { label: 'label-hidden',          text: '👻 Вне сегмента и нет в 1С',  chip: 'Скрыта полностью',      card: 'promo-card hidden-card' },
        };
        const STATUS_ORDER = ['shown', 'site_only', 'segment_blocked', 'no_site', 'hidden'];
        const STATUS_COLORS = {
            'shown': '#34c759', 'site_only': '#007aff',
            'segment_blocked': '#ff9500', 'no_site': '#ff3b30', 'hidden': '#8e8e93'
        };

        let allPromotions = [];
        let activeStatuses = new Set(STATUS_ORDER);

        function renderPromo(promo) {
            const status = promo.debug_status || 'shown';
            const meta = STATUS_META[status] || STATUS_META['shown'];
            const cardClass = debugMode ? meta.card : (promo.details_missing ? 'promo-card warning' : 'promo-card');
            const promoLink = promo.link && !promo.details_missing ? promo.link : null;

            let debugTop = '';
            if (debugMode) {
                const segInfo = promo.banner_segments && promo.banner_segments.length
                    ? `сегменты: [${promo.banner_segments.join(', ')}]`
                    : 'сегмент не ограничен';
                const pcInfo = promo.promo_code ? `promo_code: ${escapeHtml(promo.promo_code)}` : 'promo_code не задан';
                const idInfo = promo.id ? `id: ${escapeHtml(String(promo.id))}` : '';
                debugTop = `
                    <div class="debug-label ${meta.label}">${meta.text}</div>
                    <div class="debug-meta">${[pcInfo, segInfo, idInfo].filter(Boolean).join(' · ')}</div>`;
            }

            return `
            <div class="${cardClass}">
                ${debugTop}
                <div class="promo-title">${escapeHtml(promo.name)}</div>
                <div class="promo-meta">
                    ${promo.mark ? `<span class="brand-badge">${escapeHtml(promo.mark)}</span>` : ''}
                    ${promo.date_to ? `<span>до ${formatDate(promo.date_to)}</span>` : ''}
                </div>
                ${promo.image ? `<div class="promo-image"><img src="${escapeHtml(promo.image)}" alt="Превью акции"></div>` : ''}
                ${promo.description ? `<div class="promo-description">${escapeHtml(promo.description)}</div>` : ''}
                ${promo.details_missing ? `<div class="warning-text">ВНИМАНИЕ: Для этой акции нет описания на сайте!</div>` : ''}
                ${promoLink ? `<a href="#" onclick="trackClick('${escapeHtml(String(promo.id))}', '${escapeHtml(promo.name)}', '${escapeHtml(promoLink)}'); return false;" class="promo-button">Подробнее на сайте</a>` : ''}
            </div>`;
        }

        function applyFilters() {
            const search = document.getElementById('filter-search').value.trim().toLowerCase();
            const brand  = document.getElementById('filter-brand').value;

            const filtered = allPromotions.filter(p => {
                if (debugMode && !activeStatuses.has(p.debug_status || 'shown')) return false;
                if (brand && p.mark !== brand) return false;
                if (search) {
                    const segs = (p.banner_segments || []).join(' ');
                    const hay = [p.name, p.id, p.promo_code, segs].join(' ').toLowerCase();
                    if (!hay.includes(search)) return false;
                }
                return true;
            });

            const container = document.getElementById('content');
            if (!filtered.length) {
                container.innerHTML = `<div style="background:var(--card-bg);border-radius:20px;padding:40px 20px;text-align:center;">Ничего не найдено</div>`;
                document.getElementById('filter-count').textContent = '0 из ' + allPromotions.length;
                return;
            }

            if (debugMode) {
                const groups = {};
                STATUS_ORDER.forEach(s => { groups[s] = []; });
                filtered.forEach(p => { (groups[p.debug_status || 'shown'] || groups['shown']).push(p); });
                // Count by status across ALL data (not just filtered) for chip labels
                const totalByStatus = {};
                STATUS_ORDER.forEach(s => { totalByStatus[s] = 0; });
                allPromotions.forEach(p => { totalByStatus[p.debug_status || 'shown']++; });
                // Update chip counts
                STATUS_ORDER.forEach(s => {
                    const chip = document.getElementById('chip-' + s);
                    if (chip) {
                        const cnt = groups[s].length;
                        chip.querySelector('.chip-count').textContent = cnt;
                    }
                });

                const sectionTitles = {
                    'shown':           '✅ Показываются',
                    'site_only':       '🌐 Есть на сайте, нет в личном списке',
                    'segment_blocked': '🔒 Заблокированы сегментом',
                    'no_site':         '⚠️ Есть в личном списке, нет на сайте',
                    'hidden':          '👻 Вне сегмента и вне личного списка',
                };
                let html = '';
                STATUS_ORDER.forEach(s => {
                    if (groups[s].length) {
                        html += `<div class="debug-section-header">${sectionTitles[s]} (${groups[s].length})</div>`;
                        groups[s].forEach(p => { html += renderPromo(p); });
                    }
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = filtered.map(renderPromo).join('');
            }

            document.getElementById('filter-count').textContent = filtered.length + ' из ' + allPromotions.length;
        }

        function initDebugFilters() {
            document.getElementById('debug-filters').style.display = '';

            // Brand dropdown
            const marks = [...new Set(allPromotions.map(p => p.mark).filter(Boolean))].sort();
            const sel = document.getElementById('filter-brand');
            marks.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m; opt.textContent = m;
                sel.appendChild(opt);
            });

            // Status chips
            const chipsEl = document.getElementById('status-chips');
            STATUS_ORDER.forEach(s => {
                const count = allPromotions.filter(p => (p.debug_status || 'shown') === s).length;
                if (!count) return;
                const chip = document.createElement('span');
                chip.className = 'status-chip on';
                chip.id = 'chip-' + s;
                chip.style.background = STATUS_COLORS[s];
                chip.style.color = 'white';
                chip.innerHTML = `${STATUS_META[s].chip} <span class="chip-count">${count}</span>`;
                chip.addEventListener('click', () => {
                    if (activeStatuses.has(s)) {
                        activeStatuses.delete(s);
                        chip.classList.replace('on', 'off');
                    } else {
                        activeStatuses.add(s);
                        chip.classList.replace('off', 'on');
                    }
                    applyFilters();
                });
                chipsEl.appendChild(chip);
            });

            document.getElementById('filter-search').addEventListener('input', applyFilters);
            document.getElementById('filter-brand').addEventListener('change', applyFilters);
            document.getElementById('filter-reset').addEventListener('click', () => {
                document.getElementById('filter-search').value = '';
                document.getElementById('filter-brand').value = '';
                activeStatuses = new Set(STATUS_ORDER);
                document.querySelectorAll('.status-chip').forEach(c => c.classList.replace('off', 'on'));
                applyFilters();
            });
        }

        fetch(dataUrl)
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('content');
                if (data.promotions && data.promotions.length) {
                    allPromotions = data.promotions;
                    if (debugMode) {
                        initDebugFilters();
                    }
                    applyFilters();
                } else {
                    container.innerHTML = `<div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">На данный момент нет активных акций</div>`;
                }
            })
            .catch(error => {
                console.error('Ошибка загрузки акций:', error);
                document.getElementById('content').innerHTML = `<div style="background: var(--card-bg); border-radius: 20px; padding: 40px 20px; text-align: center;">Ошибка загрузки акций. Попробуйте позже.</div>`;
            });
    </script>
</body>
</html>
"""

@app.route('/promo/<partner_code>')
def promo_page(partner_code):
    return render_template_string(HTML_TEMPLATE)

# ... остальные маршруты (/click, /promo/.../data, /health, /tg) остаются без изменений. 
# Чтобы не дублировать, я добавлю их кратко, но в вашем полном файле они уже есть.
# Ниже для полноты я включу их, но вы можете оставить свои существующие.

@app.route('/tg')
def tg_redirect():
    return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Переход к боту</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script>
        window.location.href = "tg://resolve?domain=stalkerco_news_bot";
        setTimeout(function() {
            document.body.innerHTML = '<div style="text-align:center; padding:50px;"><h2>Не удалось открыть Telegram</h2><p>Пожалуйста, установите Telegram:</p><a href="https://telegram.org/dl" target="_blank" rel="noopener noreferrer">Скачать Telegram</a></div>';
        }, 1000);
    </script>
</head>
<body>Переход в Telegram...</body>
</html>'''

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

    if debug_mode:
        promotions_list = promo_client.get_promotions_list_sync(partner_code)
        promo_map = {}
        if promotions_list:
            for promo in promotions_list:
                pid = str(promo.get('id', '')).strip()
                if pid:
                    promo_map[pid] = promo

        all_banners = bitrix_client.get_banners_all_sync(partner_code) or []

        enriched = []
        matched_exchange_ids = set()

        for banner in all_banners:
            promo_code_raw = banner.get('promo_code') or ''
            promo_codes = [p.strip() for p in str(promo_code_raw).split(',') if p.strip()]
            segment_match = banner.get('segment_match', True)

            matched_promo = None
            matched_id = None
            for pc in promo_codes:
                if pc in promo_map:
                    matched_promo = promo_map[pc]
                    matched_id = pc
                    break

            in_exchange = matched_promo is not None
            if in_exchange:
                matched_exchange_ids.add(matched_id)

            if in_exchange and segment_match:
                status = 'shown'
            elif in_exchange and not segment_match:
                status = 'segment_blocked'
            elif not in_exchange and segment_match:
                status = 'site_only'
            else:
                status = 'hidden'

            if brand_filter and matched_promo:
                if matched_promo.get('mark', '').lower() != brand_filter.lower():
                    continue

            enriched.append({
                'id': matched_id or promo_code_raw or str(banner.get('id', '')),
                'promo_code': promo_code_raw,
                'banner_segments': banner.get('banner_segments', []),
                'name': clean_text(banner.get('name') or (matched_promo.get('name') if matched_promo else None) or 'Акция'),
                'description': clean_text(banner.get('description', '')),
                'image': clean_text(banner.get('image')),
                'link': clean_text(banner.get('link')),
                'mark': clean_text(matched_promo.get('mark', '') if matched_promo else '') or clean_text(banner.get('brand', '') or ''),
                'date_to': clean_text(matched_promo.get('date_to', '')) if matched_promo else '',
                'details_missing': False,
                'debug_status': status,
            })

        # Акции из exchange, которые не нашлись ни в одном баннере
        for pid, promo in promo_map.items():
            if pid in matched_exchange_ids:
                continue
            if brand_filter and promo.get('mark', '').lower() != brand_filter.lower():
                continue
            enriched.append({
                'id': pid,
                'promo_code': pid,
                'banner_segments': [],
                'name': clean_text(promo.get('name', 'Акция')),
                'description': '',
                'image': None,
                'link': None,
                'mark': clean_text(promo.get('mark', '')),
                'date_to': clean_text(promo.get('date_to', '')),
                'details_missing': False,
                'debug_status': 'no_site',
            })

        status_order = ['shown', 'site_only', 'segment_blocked', 'no_site', 'hidden']
        enriched.sort(key=lambda x: status_order.index(x.get('debug_status', 'shown')))
        return jsonify({"promotions": enriched})

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

    promotions_list = promo_client.get_promotions_list_sync(partner_code)
    if not promotions_list:
        return jsonify({"promotions": []}), 404
    promo_map = {}
    for promo in promotions_list:
        promo_id = str(promo.get('id', '')).strip()
        if promo_id:
            promo_map[promo_id] = promo
    if not promo_map:
        return jsonify({"promotions": []}), 404

    banners = bitrix_client.get_banners_sync(partner_code)
    if not banners:
        return jsonify({"promotions": []}), 404

    enriched = []
    for banner in banners:
        promo_code_raw = banner.get('promo_code') or ''
        promo_codes = [p.strip() for p in str(promo_code_raw).split(',') if p.strip()]
        matched_promo = None
        matched_id = None
        for pc in promo_codes:
            if pc in promo_map:
                matched_promo = promo_map[pc]
                matched_id = pc
                break
        if not matched_promo:
            continue
        if brand_filter:
            if matched_promo.get('mark', '').lower() != brand_filter.lower():
                continue
        enriched.append({
            'id': matched_id,
            'name': clean_text(banner.get('name')) or clean_text(matched_promo.get('name', 'Акция')),
            'description': clean_text(banner.get('description', '')),
            'image': clean_text(banner.get('image')),
            'link': clean_text(banner.get('link')),
            'mark': clean_text(matched_promo.get('mark', '')) or clean_text(banner.get('brand', '') or ''),
            'date_to': clean_text(matched_promo.get('date_to', '')),
            'details_missing': False
        })
    return jsonify({"promotions": enriched})

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)