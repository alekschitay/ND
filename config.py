#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурационный файл для телеграм-бота мониторинга концертов
"""

import os
from typing import List

# Токен бота (можно переопределить через переменную окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7711964415:AAF0tp9uhybhTZ7gPEGLNnpE6TxgvAElYzU")

# Интервал мониторинга в секундах (10 минут = 600 секунд)
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "600"))

# Максимальное количество событий для отправки в одном уведомлении
MAX_EVENTS_PER_NOTIFICATION = int(os.getenv("MAX_EVENTS_PER_NOTIFICATION", "5"))

# Максимальное количество изображений для отправки
MAX_IMAGES_PER_NOTIFICATION = int(os.getenv("MAX_IMAGES_PER_NOTIFICATION", "3"))

# Таймаут для HTTP запросов в секундах
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))

# Максимальное количество элементов для парсинга на странице
MAX_ELEMENTS_TO_PARSE = int(os.getenv("MAX_ELEMENTS_TO_PARSE", "20"))

# Файлы для хранения данных
DATA_FILE = os.getenv("DATA_FILE", "monitored_urls.json")
EVENTS_FILE = os.getenv("EVENTS_FILE", "events_cache.json")

# Селекторы для поиска событий (можно расширить)
EVENT_SELECTORS = [
    '.event', '.concert', '.show', '.performance',
    '[class*="event"]', '[class*="concert"]', '[class*="show"]',
    '.card', '.item', '.poster', '.ticket',
    '[class*="card"]', '[class*="item"]', '[class*="poster"]'
]

# Селекторы для заголовков событий
TITLE_SELECTORS = [
    'h1', 'h2', 'h3', 'h4', 
    '.title', '.name', '.event-title', '.concert-title',
    '[class*="title"]', '[class*="name"]'
]

# Селекторы для дат
DATE_SELECTORS = [
    '.date', '.time', '.datetime', 
    '[class*="date"]', '[class*="time"]', '[class*="datetime"]'
]

# Селекторы для мест проведения
VENUE_SELECTORS = [
    '.venue', '.place', '.location', '.address',
    '[class*="venue"]', '[class*="place"]', '[class*="location"]'
]

# Селекторы для цен
PRICE_SELECTORS = [
    '.price', '.cost', '.ticket', '.ticket-price',
    '[class*="price"]', '[class*="cost"]', '[class*="ticket"]'
]

# User-Agent для HTTP запросов
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки для конкретных сайтов (можно расширить)
SITE_SPECIFIC_CONFIGS = {
    # Пример конфигурации для конкретного сайта
    # "example.com": {
    #     "event_selector": ".custom-event",
    #     "title_selector": ".custom-title",
    #     "date_selector": ".custom-date"
    # }
}

# Черный список доменов (сайты, которые не стоит мониторить)
BLOCKED_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0"
]

# Минимальная длина заголовка события
MIN_TITLE_LENGTH = int(os.getenv("MIN_TITLE_LENGTH", "3"))

# Максимальная длина заголовка события
MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "200"))

# Поддерживаемые форматы изображений
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Настройки для обработки ошибок
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # секунды

# Настройки для уведомлений
NOTIFICATION_SETTINGS = {
    "enable_images": os.getenv("ENABLE_IMAGES", "true").lower() == "true",
    "enable_venue_info": os.getenv("ENABLE_VENUE_INFO", "true").lower() == "true",
    "enable_price_info": os.getenv("ENABLE_PRICE_INFO", "true").lower() == "true",
    "enable_date_info": os.getenv("ENABLE_DATE_INFO", "true").lower() == "true"
}