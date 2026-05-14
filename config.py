import os

class Config:
    SECRET_KEY = 'your-secret-key-here-change-in-production'
    OUTPUT_FOLDER = 'output'
    HISTORY_FOLDER = 'history'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Настройки для аналитики
    ANALYTICS_ENABLED = True
    
    # Поддерживаемые типы кодов
    CODE_TYPES = ['qr', 'datamatrix', 'aztec', 'pdf417']
    
    # Поддерживаемые форматы экспорта
    EXPORT_FORMATS = ['png', 'svg', 'pdf', 'eps']