#!/bin/bash

# Скрипт для автоматического перезапуска бота
echo "🔄 Перезапуск бота..."

# Останавливаем все процессы бота
pkill -9 -f "python3 concert_monitor_bot.py"

# Ждем 2 секунды
sleep 2

# Запускаем бота заново
echo "🚀 Запуск бота..."
python3 concert_monitor_bot.py &

# Проверяем, что бот запустился
sleep 5
if pgrep -f "python3 concert_monitor_bot.py" > /dev/null; then
    echo "✅ Бот успешно запущен!"
else
    echo "❌ Ошибка запуска бота!"
    exit 1
fi