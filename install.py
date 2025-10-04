#!/usr/bin/env python3
"""
Скрипт для установки зависимостей Concert Monitor Bot
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command):
    """Выполнение команды с выводом"""
    print(f"🔄 Выполняю: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Успешно")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Ошибка:")
        print(result.stderr)
        return False
    
    return True

def main():
    """Основная функция установки"""
    print("🎵 Установка Concert Monitor Bot...")
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    
    print(f"✅ Python {sys.version}")
    
    # Устанавливаем зависимости
    if not run_command("pip install -r requirements.txt"):
        print("❌ Ошибка установки зависимостей")
        sys.exit(1)
    
    # Создаем файл .env если его нет
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            run_command("cp .env.example .env")
            print("📝 Создан файл .env из .env.example")
            print("🔧 Не забудьте заполнить BOT_TOKEN в файле .env")
        else:
            print("⚠️ Файл .env.example не найден")
    
    print("\n🎉 Установка завершена!")
    print("📋 Следующие шаги:")
    print("1. Получите токен бота у @BotFather")
    print("2. Заполните BOT_TOKEN в файле .env")
    print("3. Запустите бота: python run.py")

if __name__ == '__main__':
    main()