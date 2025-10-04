#!/bin/bash

# Скрипт для запуска надежного бота
echo "🚀 Запуск надежного бота мониторинга..."

# Останавливаем все старые процессы
pkill -9 -f "python3.*bot.py"

# Ждем 2 секунды
sleep 2

# Запускаем новый бот
echo "🎵 Запуск бота..."
nohup python3 reliable_bot.py > bot.log 2>&1 &

# Проверяем запуск
sleep 5
if pgrep -f "python3 reliable_bot.py" > /dev/null; then
    echo "✅ Бот успешно запущен!"
    echo "📝 Логи: bot.log"
    echo "🔄 Мониторинг каждые 10 минут"
else
    echo "❌ Ошибка запуска бота!"
    exit 1
fi