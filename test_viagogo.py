#!/usr/bin/env python3
"""
Тест парсинга Viagogo
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from monitor import PageMonitor

async def test_viagogo():
    """Тестирование парсинга Viagogo"""
    print("🔍 Тестирую парсинг https://www.viagogo.com/Concert-Tickets/Pop-Rock/Pop")
    
    monitor = PageMonitor()
    
    try:
        result = await monitor.test_page_parsing("https://www.viagogo.com/Concert-Tickets/Pop-Rock/Pop")
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
            return
        
        print(f"📊 Результаты:")
        print(f"🔗 URL: {result['url']}")
        print(f"📄 Размер страницы: {result['content_length']} символов")
        print(f"🎵 Найдено событий: {result['events_found']}")
        
        if result['events']:
            print(f"\n📋 Примеры найденных событий:")
            for i, event in enumerate(result['events'][:5], 1):
                print(f"{i}. {event['title']}")
                if event['date']:
                    print(f"   📅 {event['date']}")
                if event['link']:
                    print(f"   🔗 {event['link']}")
                if event.get('image_url'):
                    print(f"   🖼️ Изображение: {event['image_url']}")
                print()
        else:
            print("⚠️ События не найдены")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        await monitor.close_session()

if __name__ == '__main__':
    asyncio.run(test_viagogo())