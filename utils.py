import hashlib
import json
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import re

def hash_data(data):
    """Создание хэша данных"""
    return hashlib.md5(f"{data}{datetime.now()}".encode()).hexdigest()

def validate_url(url):
    """Проверка валидности URL"""
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def save_to_history(data, filename, code_type, data_type, tags=[]):
    """Сохранение в историю"""
    history_id = hash_data(data)
    history_entry = {
        'id': history_id,
        'type': code_type,
        'data_type': data_type,
        'data': data[:100] if len(data) > 100 else data,
        'filename': filename,
        'created_at': datetime.now().isoformat(),
        'tags': tags,
        'full_data': data
    }
    
    with open(os.path.join('history', f"{history_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(history_entry, f, ensure_ascii=False, indent=2)
    
    return history_id

def load_from_history(history_id):
    """Загрузка из истории"""
    filepath = os.path.join('history', f"{history_id}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_all_history(limit=50):
    """Получение всей истории"""
    history_list = []
    for file in os.listdir('history'):
        if file.endswith('.json'):
            with open(os.path.join('history', file), 'r', encoding='utf-8') as f:
                history_list.append(json.load(f))
    
    # Сортировка по дате
    history_list.sort(key=lambda x: x['created_at'], reverse=True)
    return history_list[:limit]

def cleanup_old_files(folder, hours=24):
    """Очистка старых файлов"""
    import time
    current_time = time.time()
    deleted = 0
    
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.getctime(filepath) < current_time - (hours * 3600):
            os.remove(filepath)
            deleted += 1
    
    return deleted