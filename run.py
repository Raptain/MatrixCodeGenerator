#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Создаем необходимые папки
    os.makedirs('output', exist_ok=True)
    os.makedirs('history', exist_ok=True)
    os.makedirs('static/logos', exist_ok=True)
    os.makedirs('static/patterns', exist_ok=True)
    
    # Создаем логотип если его нет
    if not os.path.exists('static/logos/default.png'):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 100), 'white')
            draw = ImageDraw.Draw(img)
            draw.ellipse([(10, 10), (90, 90)], fill='#667eea')
            draw.rectangle([(40, 40), (60, 60)], fill='white')
            img.save('static/logos/default.png')
            print("✅ Создан логотип по умолчанию")
        except:
            print("⚠️ Не удалось создать логотип")
    
    # Запускаем приложение
    from app import app
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("=" * 60)
    print("🚀 ЗАПУСК ГЕНЕРАТОРА МАТРИЧНЫХ КОДОВ")
    print("=" * 60)
    print("📱 Локальный адрес: http://localhost:5000")
    print("=" * 60)
    print("Сервер запущен... Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    app.run(debug=True, host='localhost', port=5000, use_reloader=False)