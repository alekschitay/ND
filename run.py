#!/usr/bin/env python3
"""
Скрипт для запуска Concert Monitor Bot
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from bot import ConcertMonitorBot

async def main():
    """Основная функция запуска"""
    print("🎵 Запуск Concert Monitor Bot...")
    
    # Проверяем наличие файла .env
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Скопируйте .env.example в .env и заполните BOT_TOKEN")
        return
    
    # Проверяем наличие токена
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('BOT_TOKEN'):
        print("❌ BOT_TOKEN не установлен в файле .env!")
        print("🤖 Получите токен у @BotFather в Telegram")
        return
    
    try:
        bot = ConcertMonitorBot()
        await bot.start_bot()
    except KeyboardInterrupt:
        print("\n👋 Остановка бота...")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())