#!/usr/bin/env python3
"""
Запуск бота для мониторинга концертных площадок
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from bot_new import ConcertMonitorBot
from config_new import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден! Проверьте файл .env")
        return
    
    try:
        bot = ConcertMonitorBot()
        await bot.start_bot()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)