#!/bin/bash

# Скрипт для поддержания бота в рабочем состоянии
echo "🔄 Запуск системы поддержания бота..."

while true; do
    # Проверяем, работает ли бот
    if ! pgrep -f "python3 stable_bot.py" > /dev/null; then
        echo "⚠️ Бот не работает, перезапускаем..."
        
        # Останавливаем все процессы бота
        pkill -9 -f "python3.*bot.py"
        sleep 2
        
        # Запускаем стабильный бот
        echo "🚀 Запуск стабильного бота..."
        nohup python3 stable_bot.py > bot.log 2>&1 &
        
        # Проверяем запуск
        sleep 5
        if pgrep -f "python3 stable_bot.py" > /dev/null; then
            echo "✅ Бот успешно запущен!"
        else
            echo "❌ Ошибка запуска бота!"
        fi
    else
        echo "✅ Бот работает нормально"
    fi
    
    # Ждем 2 минуты перед следующей проверкой
    sleep 120
done