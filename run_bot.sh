#!/bin/bash

# Скрипт для запуска телеграм-бота мониторинга концертов

echo "🎵 Запуск телеграм-бота для мониторинга концертных площадок..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8 или выше."
    exit 1
fi

# Проверяем наличие pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 не найден. Установите pip."
    exit 1
fi

# Устанавливаем зависимости
echo "📦 Установка зависимостей..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi

# Создаем директории для данных если их нет
mkdir -p data

# Запускаем бота
echo "🚀 Запуск бота..."
python3 concert_monitor_bot.py