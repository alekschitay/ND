#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работы телеграм-бота
"""

import asyncio
import sys
from concert_monitor_bot import ConcertMonitorBot

async def test_parsing():
    """Тестирование парсинга событий"""
    bot = ConcertMonitorBot()
    
    # Тестовые URL для проверки
    test_urls = [
        "https://example.com/events",  # Замените на реальные URL для тестирования
        "https://httpbin.org/html",    # Тестовая страница
    ]
    
    print("🧪 Тестирование парсинга событий...")
    
    for url in test_urls:
        print(f"\n🔍 Тестирование URL: {url}")
        try:
            events = await bot.parse_events_from_page(url)
            print(f"✅ Найдено событий: {len(events)}")
            
            for i, event in enumerate(events[:3], 1):  # Показываем первые 3 события
                print(f"  {i}. {event.title}")
                print(f"     Дата: {event.date}")
                print(f"     URL: {event.url}")
                if event.image_url:
                    print(f"     Изображение: {event.image_url}")
                print()
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("✅ Тестирование завершено")

def test_config():
    """Тестирование конфигурации"""
    print("⚙️ Проверка конфигурации...")
    
    try:
        import config
        print(f"✅ Токен бота: {config.BOT_TOKEN[:10]}...")
        print(f"✅ Интервал мониторинга: {config.MONITORING_INTERVAL} секунд")
        print(f"✅ Максимум событий в уведомлении: {config.MAX_EVENTS_PER_NOTIFICATION}")
        print(f"✅ Максимум изображений: {config.MAX_IMAGES_PER_NOTIFICATION}")
        print(f"✅ Селекторов событий: {len(config.EVENT_SELECTORS)}")
        print(f"✅ Селекторов заголовков: {len(config.TITLE_SELECTORS)}")
        print("✅ Конфигурация загружена успешно")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")

def test_data_files():
    """Тестирование файлов данных"""
    print("\n📁 Проверка файлов данных...")
    
    import os
    import config
    
    # Проверяем существование файлов
    if os.path.exists(config.DATA_FILE):
        print(f"✅ Файл данных найден: {config.DATA_FILE}")
    else:
        print(f"ℹ️ Файл данных будет создан: {config.DATA_FILE}")
    
    if os.path.exists(config.EVENTS_FILE):
        print(f"✅ Файл кэша найден: {config.EVENTS_FILE}")
    else:
        print(f"ℹ️ Файл кэша будет создан: {config.EVENTS_FILE}")

async def main():
    """Основная функция тестирования"""
    print("🎵 Тестирование телеграм-бота для мониторинга концертов")
    print("=" * 60)
    
    # Тестируем конфигурацию
    test_config()
    
    # Тестируем файлы данных
    test_data_files()
    
    # Тестируем парсинг (только если указаны реальные URL)
    if len(sys.argv) > 1 and sys.argv[1] == "--test-parsing":
        await test_parsing()
    else:
        print("\n💡 Для тестирования парсинга запустите:")
        print("   python test_bot.py --test-parsing")
    
    print("\n🚀 Для запуска бота используйте:")
    print("   python concert_monitor_bot.py")
    print("   или")
    print("   ./run_bot.sh")

if __name__ == "__main__":
    asyncio.run(main())