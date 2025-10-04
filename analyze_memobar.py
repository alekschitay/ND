#!/usr/bin/env python3
"""
Анализ структуры сайта memobar.ru для поиска блока афиш
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from monitor import PageMonitor
from bs4 import BeautifulSoup

async def analyze_memobar():
    """Анализ структуры memobar.ru"""
    print("🔍 Анализирую структуру https://memobar.ru/")
    
    monitor = PageMonitor()
    
    try:
        # Загружаем страницу
        content = await monitor.fetch_page("https://memobar.ru/")
        if not content:
            print("❌ Не удалось загрузить страницу")
            return
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Ищем меню с разделом "афиши"
        print("\n📋 Ищем меню с разделом 'афиши':")
        menu_items = soup.find_all(['a', 'button'], string=lambda text: text and 'афиш' in text.lower())
        for item in menu_items:
            print(f"   - {item.get_text(strip=True)}: {item.get('href', '')}")
        
        # Ищем блоки с афишами
        print("\n🎭 Ищем блоки с афишами:")
        
        # Ищем по классам, содержащим "afisha", "poster", "event"
        afisha_selectors = [
            '[class*="afisha"]',
            '[class*="poster"]', 
            '[class*="event"]',
            '[id*="afisha"]',
            '[id*="poster"]',
            '[id*="event"]'
        ]
        
        for selector in afisha_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"\n   Селектор '{selector}' найден {len(elements)} элементов:")
                for i, elem in enumerate(elements[:3]):  # Показываем первые 3
                    print(f"   {i+1}. {elem.name} class='{elem.get('class', [])}' id='{elem.get('id', '')}'")
                    # Ищем изображения в этом элементе
                    imgs = elem.find_all('img')
                    if imgs:
                        print(f"      Изображений: {len(imgs)}")
                        for img in imgs[:2]:  # Показываем первые 2
                            src = img.get('src', '')
                            alt = img.get('alt', '')
                            print(f"      - {src} (alt: {alt})")
        
        # Ищем все изображения на странице и группируем по контейнерам
        print("\n🖼️ Анализ изображений по контейнерам:")
        all_images = soup.find_all('img')
        
        # Группируем изображения по их родительским контейнерам
        containers = {}
        for img in all_images:
            parent = img.parent
            while parent and parent.name != 'body':
                parent_class = ' '.join(parent.get('class', []))
                parent_id = parent.get('id', '')
                container_key = f"{parent.name}.{parent_class}.{parent_id}"
                
                if container_key not in containers:
                    containers[container_key] = []
                containers[container_key].append(img)
                break
        
        # Показываем контейнеры с несколькими изображениями
        for container_key, imgs in containers.items():
            if len(imgs) > 1:  # Контейнеры с несколькими изображениями
                print(f"\n   Контейнер: {container_key}")
                print(f"   Изображений: {len(imgs)}")
                for img in imgs[:3]:  # Показываем первые 3
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    print(f"   - {src} (alt: {alt})")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        await monitor.close_session()

if __name__ == '__main__':
    asyncio.run(analyze_memobar())