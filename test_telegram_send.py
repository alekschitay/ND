#!/usr/bin/env python3
"""
Тест отправки изображения в Telegram
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from telegram import Bot
import config

async def test_telegram_send():
    """Тест отправки изображения в Telegram"""
    print("🔍 Тестирую отправку изображения в Telegram")
    
    bot = Bot(token=config.BOT_TOKEN)
    
    # Тестовое изображение с memobar.ru
    test_image_url = "https://thb.tildacdn.com/tild3736-3264-4236-b866-623662396236/-/empty/memo_21102021-027_4_.jpg"
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        
        # Отправляем тестовое сообщение
        await bot.send_message(
            chat_id=bot_info.id,  # Отправляем самому себе
            text="🧪 Тест отправки изображения"
        )
        
        # Отправляем изображение
        print(f"📸 Отправляю изображение: {test_image_url}")
        
        await bot.send_photo(
            chat_id=bot_info.id,
            photo=test_image_url,
            caption="🎵 Тестовая афиша с memobar.ru"
        )
        
        print("✅ Изображение отправлено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print(f"Тип ошибки: {type(e).__name__}")

if __name__ == '__main__':
    asyncio.run(test_telegram_send())