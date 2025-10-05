#!/bin/bash
echo "🔄 Запуск системы поддержания финального бота..."

while true; do
    if ! pgrep -f "python3 final_bot.py" > /dev/null; then
        echo "⚠️ Бот не работает, перезапускаем..."
        pkill -9 -f "python3.*bot.py"
        sleep 2
        echo "🚀 Запуск финального бота..."
        nohup python3 final_bot.py > bot.log 2>&1 &
        sleep 5
        if pgrep -f "python3 final_bot.py" > /dev/null; then
            echo "✅ Бот успешно запущен!"
        else
            echo "❌ Ошибка запуска бота!"
        fi
    else
        echo "✅ Бот работает нормально"
    fi
    sleep 60
done