"""
Конфигурация бота для мониторинга концертных площадок
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Путь к базе данных
DATABASE_PATH = 'concert_monitor.db'

# Интервал проверки страниц (в минутах)
CHECK_INTERVAL_MINUTES = 5

# Максимальное количество событий за одну проверку
MAX_EVENTS_PER_CHECK = 10

# Настройки HTTP запросов
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # Задержка между запросами в секундах

# Настройки парсинга
MIN_IMAGE_SIZE = 100  # Минимальный размер изображения в пикселях
MAX_IMAGE_SIZE = 5000  # Максимальный размер изображения в пикселях

# Ключевые слова для фильтрации событий
EVENT_KEYWORDS = [
    'концерт', 'concert', 'фестиваль', 'festival', 'выступление', 'performance',
    'шоу', 'show', 'тур', 'tour', 'гастроли', 'tour', 'афиша', 'poster',
    'билет', 'ticket', 'событие', 'event', 'музыка', 'music'
]

# Исключаемые ключевые слова для изображений
EXCLUDE_IMAGE_KEYWORDS = [
    'logo', 'icon', 'avatar', 'profile', 'banner', 'header', 'footer',
    'social', 'share', 'like', 'comment', 'analytics', 'tracking',
    'pixel', 'beacon', 'yandex', 'google', 'facebook', 'twitter',
    'instagram', 'vk', 'telegram', 'whatsapp', 'youtube', 'vimeo'
]

# Поддерживаемые форматы изображений
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

# Настройки логирования
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'