#!/usr/bin/env python3
"""
Тестирование основных компонентов приложения
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестируем импорты основных модулей"""
    try:
        print("Тестирование импортов...")
        
        # Тестируем конфигурацию
        from app.config import settings
        print("✓ Конфигурация загружена")
        
        # Тестируем модели
        from app.models import MonitoredSite, Event, Notification
        print("✓ Модели базы данных загружены")
        
        # Тестируем скрапер
        from app.scraper import EventScraper
        print("✓ Веб-скрапер загружен")
        
        # Тестируем уведомления
        from app.notifications import NotificationService
        print("✓ Система уведомлений загружена")
        
        # Тестируем планировщик
        from app.scheduler import MonitoringScheduler
        print("✓ Планировщик загружен")
        
        print("\n✅ Все модули успешно импортированы!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_scraper():
    """Тестируем скрапер на простом примере"""
    try:
        print("\nТестирование скрапера...")
        
        from app.scraper import EventScraper
        scraper = EventScraper()
        
        # Тестируем на простом HTML
        test_html = """
        <html>
        <body>
            <div class="event-item">
                <h3>Тестовый концерт</h3>
                <a href="/event/123">Подробнее</a>
                <p>Описание события</p>
            </div>
        </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(test_html, 'html.parser')
        events = scraper._parse_events(soup.select('.event-item'), 'https://example.com')
        
        if events:
            print(f"✓ Найдено {len(events)} событий")
            print(f"✓ Первое событие: {events[0]['title']}")
        else:
            print("❌ События не найдены")
            return False
            
        print("✅ Скрапер работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в скрапере: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🎵 Concert Monitor - Тестирование компонентов\n")
    
    success = True
    
    # Тестируем импорты
    if not test_imports():
        success = False
    
    # Тестируем скрапер
    if not test_scraper():
        success = False
    
    print("\n" + "="*50)
    if success:
        print("🎉 Все тесты прошли успешно!")
        print("Приложение готово к запуску.")
    else:
        print("❌ Некоторые тесты не прошли.")
        print("Проверьте зависимости и настройки.")
    
    return success

if __name__ == "__main__":
    main()