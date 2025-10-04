#!/usr/bin/env python3
"""
Простой скрипт для просмотра демо в терминале
"""

import webbrowser
import time
import subprocess
import sys

def main():
    print("🎵 Concert Monitor - Демо")
    print("=" * 50)
    
    # Проверяем, что сервер запущен
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
        if response.getcode() == 200:
            print("✅ Сервер работает на http://localhost:8000/")
        else:
            print("❌ Сервер не отвечает")
            return
    except Exception as e:
        print(f"❌ Ошибка подключения к серверу: {e}")
        print("💡 Попробуйте запустить: python3 simple_server.py")
        return
    
    print("\n🌐 Доступные ссылки:")
    print("1. Главная страница: http://localhost:8000/")
    print("2. API сайтов: http://localhost:8000/api/sites")
    print("3. API событий: http://localhost:8000/api/events")
    print("4. Health check: http://localhost:8000/health")
    
    print("\n📱 Что вы увидите:")
    print("• Красивый интерфейс мониторинга концертных площадок")
    print("• Статистику: 3 сайта, 3 события, 2 новых")
    print("• Список площадок: Крокус Сити Холл, Олимпийский, СК Олимпийский")
    print("• Последние события с афишами")
    print("• Интерактивные кнопки управления")
    
    print("\n🎯 Основные возможности:")
    print("• Автоматический мониторинг каждые 10 минут")
    print("• Уведомления только при новых событиях")
    print("• Поддержка графических афиш")
    print("• Гибкие CSS селекторы")
    print("• Веб-интерфейс для управления")
    
    # Попытка открыть в браузере
    try:
        print("\n🚀 Открываю в браузере...")
        webbrowser.open('http://localhost:8000/')
        print("✅ Страница должна открыться в браузере")
    except Exception as e:
        print(f"❌ Не удалось открыть браузер: {e}")
        print("💡 Скопируйте ссылку вручную: http://localhost:8000/")
    
    print("\n" + "=" * 50)
    print("🎉 Демо готово к просмотру!")

if __name__ == "__main__":
    main()