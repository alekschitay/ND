#!/bin/bash

# Скрипт для мониторинга и автоматического перезапуска бота
echo "🔍 Запуск мониторинга бота..."

while true; do
    # Проверяем, работает ли бот
    if ! pgrep -f "python3 concert_monitor_bot.py" > /dev/null; then
        echo "⚠️ Бот не работает, перезапускаем..."
        ./restart_bot.sh
    else
        echo "✅ Бот работает нормально"
    fi
    
    # Ждем 5 минут перед следующей проверкой
    sleep 300
done