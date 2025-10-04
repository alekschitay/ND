#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отправки изображений
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from monitor import PageMonitor

async def test_image_send():
    """Тестирование отправки изображений"""
    print("🔍 Тестирую отправку изображений с https://memobar.ru/")
    
    monitor = PageMonitor()
    
    try:
        # Загружаем страницу
        content = await monitor.fetch_page("https://memobar.ru/")
        if not content:
            print("❌ Не удалось загрузить страницу")
            return
        
        # Извлекаем события
        events = monitor.extract_events_from_html(content, "https://memobar.ru/")
        
        print(f"📊 Найдено событий: {len(events)}")
        
        for i, event in enumerate(events, 1):
            print(f"\n{i}. {event['title']}")
            if event.get('image_url'):
                print(f"   🖼️ Изображение: {event['image_url']}")
                
                # Проверяем доступность изображения
                try:
                    session = await monitor._get_session()
                    async with session.head(event['image_url']) as response:
                        print(f"   📊 Статус: {response.status}")
                        print(f"   📏 Размер: {response.headers.get('content-length', 'неизвестно')} байт")
                        print(f"   🎨 Тип: {response.headers.get('content-type', 'неизвестно')}")
                        
                        if response.status == 200:
                            print("   ✅ Изображение доступно")
                        else:
                            print("   ❌ Изображение недоступно")
                except Exception as e:
                    print(f"   ❌ Ошибка проверки: {e}")
            else:
                print("   ❌ Нет изображения")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        await monitor.close_session()

if __name__ == '__main__':
    asyncio.run(test_image_send())