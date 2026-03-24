import asyncio
import requests
import xml.etree.ElementTree as ET
import logging
import os
import base64

logger = logging.getLogger(__name__)

def get_soap_config():
    """Возвращает конфигурацию SOAP из переменных окружения."""
    return {
        "url": os.getenv("SOAP_URL", "https://exchange.mirlk.ru/v82/ws/site.1cws"),
        "username": os.getenv("SOAP_USERNAME"),
        "password": os.getenv("SOAP_PASSWORD"),
        "action": os.getenv("SOAP_ACTION", ""),
        "idsite": os.getenv("IDSITE", "113")
    }

def build_soap_request(phone=None, partner_id=None):
    """Формирует тело SOAP-запроса в зависимости от переданных параметров."""
    config = get_soap_config()
    if partner_id:
        # Запрос по ID партнёра
        return f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <UrGetPartner xmlns="http://www.sample-package.org">
      <IDSite>{config['idsite']}</IDSite>
      <IDPartner>{partner_id}</IDPartner>
      <Phone></Phone>
      <Email></Email>
      <Version>2</Version>
      <Other></Other>
    </UrGetPartner>
  </soap:Body>
</soap:Envelope>'''
    else:
        # Запрос по телефону (как раньше)
        return f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <UrGetPartner xmlns="http://www.sample-package.org">
      <IDSite>{config['idsite']}</IDSite>
      <IDPartner></IDPartner>
      <Phone>{phone}</Phone>
      <Email></Email>
      <Version>2</Version>
      <Other></Other>
    </UrGetPartner>
  </soap:Body>
</soap:Envelope>'''

def parse_soap_response(xml_response):
    """Парсит ответ и возвращает список компаний."""
    companies = []
    try:
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'm': 'http://www.sample-package.org',
            'ns2': 'http://www.sample-package2.org'
        }
        root = ET.fromstring(xml_response)
        return_elem = root.find('.//m:return', namespaces)
        if return_elem is not None:
            for value in return_elem.findall('.//ns2:Value', namespaces):
                code_elem = value.find('ns2:Code', namespaces)
                name_elem = value.find('ns2:Name', namespaces)
                if code_elem is not None and name_elem is not None and code_elem.text and name_elem.text:
                    companies.append({
                        'code': code_elem.text,
                        'name': name_elem.text
                    })
    except Exception as e:
        logger.error(f"Ошибка парсинга SOAP-ответа: {e}")
    return companies

async def get_companies_by_phone(phone):
    """Запрос компаний по номеру телефона."""
    config = get_soap_config()
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    phone_clean = digits

    soap_body = build_soap_request(phone=phone_clean)
    credentials = f"{config['username']}:{config['password']}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'Authorization': f'Basic {encoded_credentials}'
    }
    if config['action']:
        headers['SOAPAction'] = config['action']

    logger.info(f"SOAP запрос к {config['url']}")
    try:
        response = await asyncio.to_thread(
            requests.post, config['url'], data=soap_body, headers=headers, timeout=30
        )
        logger.info(f"SOAP ответ: статус {response.status_code}")
        if response.status_code == 200:
            companies = parse_soap_response(response.text)
            logger.info(f"Получено компаний: {len(companies)} для телефона {phone_clean}")
            return companies
        else:
            logger.error(f"Ошибка SOAP-запроса: {response.status_code} {response.text[:200]}")
            return []
    except Exception as e:
        logger.error(f"Исключение при SOAP-запросе: {e}")
        return []

async def get_partner_by_id(partner_id: str):
    """Запрос информации о контрагенте по его ID."""
    config = get_soap_config()
    soap_body = build_soap_request(partner_id=partner_id)
    credentials = f"{config['username']}:{config['password']}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'Authorization': f'Basic {encoded_credentials}'
    }
    if config['action']:
        headers['SOAPAction'] = config['action']

    logger.info(f"SOAP запрос к {config['url']} для IDPartner={partner_id}")
    try:
        response = await asyncio.to_thread(
            requests.post, config['url'], data=soap_body, headers=headers, timeout=30
        )
        if response.status_code == 200:
            companies = parse_soap_response(response.text)
            if companies:
                return companies[0]
            else:
                logger.warning(f"Контрагент с ID {partner_id} не найден")
                return None
        else:
            logger.error(f"Ошибка SOAP-запроса: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Исключение при SOAP-запросе: {e}")
        return None