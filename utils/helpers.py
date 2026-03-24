import re
from typing import Optional
from config import STATIC_ADMINS, STATIC_MANAGERS
import database as db

def is_admin(user_id: int) -> bool:
    if user_id in STATIC_ADMINS:
        return True
    return any(admin["id"] == user_id for admin in db.get_db_admins())

def is_manager(user_id: int) -> bool:
    if user_id in STATIC_MANAGERS:
        return True
    return any(manager["id"] == user_id for manager in db.get_db_managers())

def clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</?[a-z][^>]*>', '', text, flags=re.IGNORECASE)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def clean_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if url.startswith(('http://', 'https://')):
        return url
    if url.startswith('//'):
        return 'https:' + url
    return 'https://' + url

def decline_ball(number: int) -> str:
    """
    Возвращает правильное склонение слова "балл" для числа.
    Пример: 1 балл, 2 балла, 5 баллов.
    """
    number = abs(number) % 100
    if 11 <= number <= 19:
        return "баллов"
    last_digit = number % 10
    if last_digit == 1:
        return "балл"
    if 2 <= last_digit <= 4:
        return "балла"
    return "баллов"