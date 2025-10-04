#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот для мониторинга концертных площадок
"""

import asyncio
import logging
import json
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Импортируем конфигурацию
from config import *

# Настройка логирования
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

@dataclass
class ConcertEvent:
    """Класс для представления концертного события"""
    title: str
    date: str
    url: str
    image_url: Optional[str] = None
    venue: Optional[str] = None
    price: Optional[str] = None

@dataclass
class MonitoredUrl:
    """Класс для отслеживаемой ссылки"""
    url: str
    user_id: int
    last_check: str
    last_hash: str
    events: List[ConcertEvent]

class ConcertMonitorBot:
    """Основной класс телеграм-бота для мониторинга концертов"""
    
    def __init__(self):
        self.monitored_urls: Dict[str, MonitoredUrl] = {}
        self.events_cache: Dict[str, Set[str]] = {}
        self.load_data()
        
    def load_data(self):
        """Загрузка данных из файлов"""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for url, url_data in data.items():
                        events = [ConcertEvent(**event) for event in url_data.get('events', [])]
                        self.monitored_urls[url] = MonitoredUrl(
                            url=url_data['url'],
                            user_id=url_data['user_id'],
                            last_check=url_data['last_check'],
                            last_hash=url_data['last_hash'],
                            events=events
                        )
            
            if os.path.exists(EVENTS_FILE):
                with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events_cache = {k: set(v) for k, v in data.items()}
                    
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
    
    def save_data(self):
        """Сохранение данных в файлы"""
        try:
            # Сохраняем отслеживаемые URL
            data = {}
            for url, monitored in self.monitored_urls.items():
                data[url] = {
                    'url': monitored.url,
                    'user_id': monitored.user_id,
                    'last_check': monitored.last_check,
                    'last_hash': monitored.last_hash,
                    'events': [asdict(event) for event in monitored.events]
                }
            
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Сохраняем кэш событий
            cache_data = {k: list(v) for k, v in self.events_cache.items()}
            with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
🎵 Добро пожаловать в бот мониторинга концертных площадок!

Этот бот поможет вам отслеживать новые события на сайтах концертных площадок.

📋 Основные команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/status - показать статус мониторинга

🔍 Команды сканирования:
/scan - принудительно сканировать все ссылки
/scan <номер> - сканировать конкретную ссылку
/test <ссылка> - протестировать парсинг ссылки
/logs - показать последние проверки

🔧 Команды настройки:
/analyze <ссылка> - проанализировать структуру сайта
/config <домен> <селектор> - настроить селекторы

Просто отправьте ссылку на страницу с событиями, и я начну её отслеживать!
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🔍 Как использовать бота:

1. Отправьте ссылку на страницу с событиями концертной площадки
2. Бот начнет мониторить эту страницу каждые 10 минут
3. При появлении новых событий вы получите уведомление

📝 Формат уведомлений:
• Название события
• Дата проведения
• Ссылка на событие
• Афиша (если доступна)

⚙️ Основные команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/status - показать статус мониторинга

🔍 Команды сканирования:
/scan - принудительно сканировать все ваши ссылки
/scan <номер> - сканировать конкретную ссылку
/test <ссылка> - протестировать парсинг ссылки
/logs - показать последние проверки ссылок

🔧 Команды настройки:
/analyze <ссылка> - проанализировать структуру сайта
/config <домен> <селектор> - настроить селекторы для сайта

💡 Совет: Добавляйте ссылки на конкретные разделы сайтов (например, /events, /concerts, /afisha)
        """
        await update.message.reply_text(help_text)
    
    async def add_url_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /add"""
        if not context.args:
            await update.message.reply_text("❌ Пожалуйста, укажите ссылку для мониторинга.\nПример: /add https://example.com/events")
            return
        
        url = context.args[0]
        user_id = update.effective_user.id
        
        # Проверяем валидность URL
        if not self.is_valid_url(url):
            await update.message.reply_text("❌ Неверный формат ссылки. Пожалуйста, укажите корректный URL.")
            return
        
        # Проверяем, не отслеживается ли уже эта ссылка
        if url in self.monitored_urls:
            await update.message.reply_text("⚠️ Эта ссылка уже отслеживается!")
            return
        
        # Добавляем новую ссылку для мониторинга
        self.monitored_urls[url] = MonitoredUrl(
            url=url,
            user_id=user_id,
            last_check=datetime.now().isoformat(),
            last_hash="",
            events=[]
        )
        
        self.save_data()
        
        await update.message.reply_text(f"✅ Ссылка добавлена для мониторинга!\n🔗 {url}\n\nБот будет проверять обновления каждые 10 минут.")
    
    async def list_urls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /list"""
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        if not user_urls:
            await update.message.reply_text("📝 У вас нет отслеживаемых ссылок.\n\nДобавьте ссылку командой /add <ссылка>")
            return
        
        text = "📋 Ваши отслеживаемые ссылки:\n\n"
        for i, url in enumerate(user_urls, 1):
            monitored = self.monitored_urls[url]
            last_check = datetime.fromisoformat(monitored.last_check).strftime("%d.%m.%Y %H:%M")
            text += f"{i}. {url}\n   Последняя проверка: {last_check}\n\n"
        
        await update.message.reply_text(text)
    
    async def remove_url_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /remove"""
        if not context.args:
            await update.message.reply_text("❌ Пожалуйста, укажите номер ссылки для удаления.\nПример: /remove 1")
            return
        
        try:
            index = int(context.args[0]) - 1
            user_id = update.effective_user.id
            user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
            
            if index < 0 or index >= len(user_urls):
                await update.message.reply_text("❌ Неверный номер ссылки.")
                return
            
            url_to_remove = user_urls[index]
            del self.monitored_urls[url_to_remove]
            
            # Удаляем из кэша событий
            if url_to_remove in self.events_cache:
                del self.events_cache[url_to_remove]
            
            self.save_data()
            
            await update.message.reply_text(f"✅ Ссылка удалена из мониторинга:\n{url_to_remove}")
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат номера. Укажите число.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        total_urls = len(self.monitored_urls)
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        status_text = f"""
📊 Статус мониторинга:

🔗 Всего отслеживаемых ссылок: {total_urls}
👤 Ваших ссылок: {len(user_urls)}
⏰ Интервал проверки: {MONITORING_INTERVAL // 60} минут
🔄 Текущее время: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}

{'✅ Мониторинг активен' if total_urls > 0 else '⏸️ Мониторинг неактивен'}
        """
        
        if user_urls:
            status_text += "\n📋 Ваши ссылки:\n"
            for i, url in enumerate(user_urls, 1):
                monitored = self.monitored_urls[url]
                last_check = datetime.fromisoformat(monitored.last_check).strftime("%d.%m.%Y %H:%M")
                events_count = len(monitored.events)
                status_text += f"{i}. {url[:50]}...\n"
                status_text += f"   Последняя проверка: {last_check}\n"
                status_text += f"   Найдено событий: {events_count}\n\n"
        
        await update.message.reply_text(status_text)
    
    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /scan - принудительное сканирование"""
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        if not user_urls:
            await update.message.reply_text("❌ У вас нет отслеживаемых ссылок для сканирования.")
            return
        
        # Проверяем, есть ли номер конкретной ссылки
        if context.args:
            try:
                index = int(context.args[0]) - 1
                if index < 0 or index >= len(user_urls):
                    await update.message.reply_text("❌ Неверный номер ссылки.")
                    return
                
                url_to_scan = user_urls[index]
                monitored = self.monitored_urls[url_to_scan]
                
                await update.message.reply_text(f"🔍 Сканирование ссылки {index + 1}...")
                
                # Принудительное сканирование конкретной ссылки
                await self.force_scan_url(url_to_scan, monitored, update, context)
                
            except ValueError:
                await update.message.reply_text("❌ Неверный формат номера. Укажите число.")
        else:
            # Сканирование всех ссылок пользователя
            await update.message.reply_text(f"🔍 Начинаю сканирование {len(user_urls)} ссылок...")
            
            for i, url in enumerate(user_urls, 1):
                monitored = self.monitored_urls[url]
                await update.message.reply_text(f"📡 Сканирование {i}/{len(user_urls)}: {url[:50]}...")
                
                await self.force_scan_url(url, monitored, update, context)
                
                # Небольшая пауза между сканированиями
                await asyncio.sleep(1)
            
            await update.message.reply_text("✅ Сканирование всех ссылок завершено!")
    
    async def force_scan_url(self, url: str, monitored: MonitoredUrl, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Принудительное сканирование конкретного URL"""
        try:
            logger.info(f"Принудительное сканирование {url} для пользователя {update.effective_user.id}")
            
            # Парсим события
            current_events = await self.parse_events_from_page(url)
            current_hash = self.get_page_hash(current_events)
            
            # Определяем новые события
            old_event_hashes = self.events_cache.get(url, set())
            new_events = []
            
            for event in current_events:
                event_hash = hashlib.md5(f"{event.title}|{event.date}".encode('utf-8')).hexdigest()
                if event_hash not in old_event_hashes:
                    new_events.append(event)
                    old_event_hashes.add(event_hash)
            
            # Обновляем кэш
            self.events_cache[url] = old_event_hashes
            
            # Обновляем данные
            monitored.last_check = datetime.now().isoformat()
            monitored.last_hash = current_hash
            monitored.events = current_events
            
            self.save_data()
            
            # Отправляем результат сканирования
            result_text = f"""
📊 Результат сканирования:
🔗 {url}

📅 Найдено событий: {len(current_events)}
🆕 Новых событий: {len(new_events)}
🔄 Последняя проверка: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
            """
            
            if current_events:
                result_text += "\n📋 Последние события:\n"
                for i, event in enumerate(current_events[:3], 1):
                    result_text += f"{i}. {event.title}\n"
                    result_text += f"   📆 {event.date}\n"
                    if event.venue:
                        result_text += f"   📍 {event.venue}\n"
                    result_text += "\n"
            
            if new_events:
                result_text += f"\n🎉 Обнаружены новые события! Отправляю уведомления..."
                await self.send_new_events_notification(monitored.user_id, url, new_events, context.application)
            
            await update.message.reply_text(result_text)
            
        except Exception as e:
            error_text = f"❌ Ошибка сканирования {url}:\n{str(e)}"
            logger.error(f"Ошибка принудительного сканирования {url}: {e}")
            await update.message.reply_text(error_text)
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test - тестирование парсинга ссылки"""
        if not context.args:
            await update.message.reply_text("❌ Пожалуйста, укажите ссылку для тестирования.\nПример: /test https://example.com/events")
            return
        
        url = context.args[0]
        
        if not self.is_valid_url(url):
            await update.message.reply_text("❌ Неверный формат ссылки. Пожалуйста, укажите корректный URL.")
            return
        
        await update.message.reply_text(f"🧪 Тестирование парсинга ссылки...\n🔗 {url}")
        
        try:
            # Парсим события
            events = await self.parse_events_from_page(url)
            
            result_text = f"""
🧪 Результат тестирования:
🔗 {url}

📅 Найдено событий: {len(events)}
⏰ Время тестирования: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
            """
            
            if events:
                result_text += "\n📋 Найденные события:\n"
                for i, event in enumerate(events[:5], 1):
                    result_text += f"{i}. {event.title}\n"
                    result_text += f"   📆 {event.date}\n"
                    if event.venue:
                        result_text += f"   📍 {event.venue}\n"
                    if event.price:
                        result_text += f"   💰 {event.price}\n"
                    result_text += f"   🔗 {event.url}\n\n"
                
                if len(events) > 5:
                    result_text += f"... и ещё {len(events) - 5} событий"
            else:
                result_text += "\n⚠️ События не найдены. Возможно, нужно настроить селекторы для этого сайта."
                result_text += "\n\n🔍 Попробуйте команду /analyze для анализа структуры сайта."
            
            await update.message.reply_text(result_text)
            
        except Exception as e:
            error_text = f"❌ Ошибка тестирования {url}:\n{str(e)}"
            logger.error(f"Ошибка тестирования {url}: {e}")
            await update.message.reply_text(error_text)
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analyze - анализ структуры сайта"""
        if not context.args:
            await update.message.reply_text("❌ Пожалуйста, укажите ссылку для анализа.\nПример: /analyze https://example.com/events")
            return
        
        url = context.args[0]
        
        if not self.is_valid_url(url):
            await update.message.reply_text("❌ Неверный формат ссылки. Пожалуйста, укажите корректный URL.")
            return
        
        await update.message.reply_text(f"🔍 Анализ структуры сайта...\n🔗 {url}")
        
        try:
            headers = {'User-Agent': USER_AGENT}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=HTTP_TIMEOUT, headers=headers) as response:
                    if response.status != 200:
                        await update.message.reply_text(f"❌ Ошибка загрузки страницы: статус {response.status}")
                        return
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Анализируем структуру
                    analysis_text = f"""
🔍 Анализ структуры сайта:
🔗 {url}

📊 Общая информация:
• Размер страницы: {len(html)} символов
• Количество тегов: {len(soup.find_all())}
• Заголовок страницы: {soup.title.string if soup.title else 'Не найден'}
                    """
                    
                    # Ищем потенциальные контейнеры событий
                    potential_containers = []
                    
                    # Ищем по классам
                    for tag in ['div', 'article', 'section']:
                        elements = soup.find_all(tag, class_=True)
                        for elem in elements:
                            class_name = ' '.join(elem.get('class', []))
                            if any(keyword in class_name.lower() for keyword in ['event', 'concert', 'show', 'card', 'item', 'poster', 'anons']):
                                potential_containers.append({
                                    'tag': tag,
                                    'class': class_name,
                                    'text_preview': elem.get_text(strip=True)[:100]
                                })
                    
                    if potential_containers:
                        analysis_text += "\n🎯 Найденные потенциальные контейнеры событий:\n"
                        for i, container in enumerate(potential_containers[:10], 1):
                            analysis_text += f"{i}. <{container['tag']}> class='{container['class']}'\n"
                            analysis_text += f"   Текст: {container['text_preview']}...\n\n"
                    
                    # Ищем заголовки
                    headers_found = []
                    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        elements = soup.find_all(tag)
                        for elem in elements:
                            text = elem.get_text(strip=True)
                            if text and len(text) > 3:
                                headers_found.append({
                                    'tag': tag,
                                    'text': text[:50],
                                    'class': ' '.join(elem.get('class', []))
                                })
                    
                    if headers_found:
                        analysis_text += "\n📋 Найденные заголовки:\n"
                        for i, header in enumerate(headers_found[:10], 1):
                            analysis_text += f"{i}. <{header['tag']}> {header['text']}\n"
                            if header['class']:
                                analysis_text += f"   class='{header['class']}'\n"
                            analysis_text += "\n"
                    
                    # Ищем ссылки
                    links_found = []
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        if text and len(text) > 3:
                            links_found.append({
                                'href': href,
                                'text': text[:50],
                                'class': ' '.join(link.get('class', []))
                            })
                    
                    if links_found:
                        analysis_text += "\n🔗 Найденные ссылки:\n"
                        for i, link in enumerate(links_found[:10], 1):
                            analysis_text += f"{i}. {link['text']}\n"
                            analysis_text += f"   href='{link['href']}'\n"
                            if link['class']:
                                analysis_text += f"   class='{link['class']}'\n"
                            analysis_text += "\n"
                    
                    # Предлагаем селекторы
                    analysis_text += "\n💡 Рекомендуемые селекторы:\n"
                    
                    if potential_containers:
                        for container in potential_containers[:3]:
                            analysis_text += f"• .{container['class'].split()[0]}\n"
                    
                    analysis_text += "\n🔧 Для настройки селекторов используйте команду /config"
                    
                    await update.message.reply_text(analysis_text)
                    
        except Exception as e:
            error_text = f"❌ Ошибка анализа {url}:\n{str(e)}"
            logger.error(f"Ошибка анализа {url}: {e}")
            await update.message.reply_text(error_text)
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /logs - просмотр последних логов"""
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        if not user_urls:
            await update.message.reply_text("❌ У вас нет отслеживаемых ссылок.")
            return
        
        logs_text = "📋 Последние проверки ваших ссылок:\n\n"
        
        for i, url in enumerate(user_urls, 1):
            monitored = self.monitored_urls[url]
            last_check = datetime.fromisoformat(monitored.last_check)
            time_diff = datetime.now() - last_check
            
            logs_text += f"{i}. {url[:40]}...\n"
            logs_text += f"   📅 Последняя проверка: {last_check.strftime('%d.%m.%Y %H:%M:%S')}\n"
            
            if time_diff.total_seconds() < 60:
                logs_text += f"   ⏰ {int(time_diff.total_seconds())} секунд назад\n"
            elif time_diff.total_seconds() < 3600:
                logs_text += f"   ⏰ {int(time_diff.total_seconds() // 60)} минут назад\n"
            else:
                logs_text += f"   ⏰ {int(time_diff.total_seconds() // 3600)} часов назад\n"
            
            logs_text += f"   📊 Найдено событий: {len(monitored.events)}\n"
            logs_text += f"   🔄 Статус: {'✅ Активен' if time_diff.total_seconds() < MONITORING_INTERVAL * 2 else '⚠️ Долго не проверялся'}\n\n"
        
        await update.message.reply_text(logs_text)
    
    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /config - настройка селекторов для сайта"""
        if not context.args:
            await update.message.reply_text("""
🔧 Настройка селекторов для сайта

Использование:
/config <домен> <селектор_событий> [селектор_заголовка] [селектор_даты]

Примеры:
/config sohorooms.com ".event-card" ".event-title" ".event-date"
/config example.com ".concert-item" "h3" ".date"
            """)
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Недостаточно параметров. Нужно указать домен и селектор событий.")
            return
        
        domain = context.args[0]
        event_selector = context.args[1]
        title_selector = context.args[2] if len(context.args) > 2 else None
        date_selector = context.args[3] if len(context.args) > 3 else None
        
        # Обновляем конфигурацию
        if domain not in SITE_SPECIFIC_CONFIGS:
            SITE_SPECIFIC_CONFIGS[domain] = {}
        
        SITE_SPECIFIC_CONFIGS[domain]['event_selector'] = event_selector
        if title_selector:
            SITE_SPECIFIC_CONFIGS[domain]['title_selector'] = title_selector
        if date_selector:
            SITE_SPECIFIC_CONFIGS[domain]['date_selector'] = date_selector
        
        # Сохраняем конфигурацию
        try:
            import config
            config.SITE_SPECIFIC_CONFIGS = SITE_SPECIFIC_CONFIGS
            
            # Записываем в файл
            config_content = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Конфигурационный файл для телеграм-бота мониторинга концертов
\"\"\"

import os
from typing import List

# Токен бота (можно переопределить через переменную окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7711964415:AAF0tp9uhybhTZ7gPEGLNnpE6TxgvAElYzU")

# Интервал мониторинга в секундах (10 минут = 600 секунд)
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "600"))

# Максимальное количество событий для отправки в одном уведомлении
MAX_EVENTS_PER_NOTIFICATION = int(os.getenv("MAX_EVENTS_PER_NOTIFICATION", "5"))

# Максимальное количество изображений для отправки
MAX_IMAGES_PER_NOTIFICATION = int(os.getenv("MAX_IMAGES_PER_NOTIFICATION", "3"))

# Таймаут для HTTP запросов в секундах
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))

# Максимальное количество элементов для парсинга на странице
MAX_ELEMENTS_TO_PARSE = int(os.getenv("MAX_ELEMENTS_TO_PARSE", "20"))

# Файлы для хранения данных
DATA_FILE = os.getenv("DATA_FILE", "monitored_urls.json")
EVENTS_FILE = os.getenv("EVENTS_FILE", "events_cache.json")

# Селекторы для поиска событий (можно расширить)
EVENT_SELECTORS = [
    '.event', '.concert', '.show', '.performance',
    '[class*="event"]', '[class*="concert"]', '[class*="show"]',
    '.card', '.item', '.poster', '.ticket',
    '[class*="card"]', '[class*="item"]', '[class*="poster"]'
]

# Селекторы для заголовков событий
TITLE_SELECTORS = [
    'h1', 'h2', 'h3', 'h4', 
    '.title', '.name', '.event-title', '.concert-title',
    '[class*="title"]', '[class*="name"]'
]

# Селекторы для дат
DATE_SELECTORS = [
    '.date', '.time', '.datetime', 
    '[class*="date"]', '[class*="time"]', '[class*="datetime"]'
]

# Селекторы для мест проведения
VENUE_SELECTORS = [
    '.venue', '.place', '.location', '.address',
    '[class*="venue"]', '[class*="place"]', '[class*="location"]'
]

# Селекторы для цен
PRICE_SELECTORS = [
    '.price', '.cost', '.ticket', '.ticket-price',
    '[class*="price"]', '[class*="cost"]', '[class*="ticket"]'
]

# User-Agent для HTTP запросов
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки для конкретных сайтов (можно расширить)
SITE_SPECIFIC_CONFIGS = {SITE_SPECIFIC_CONFIGS}

# Черный список доменов (сайты, которые не стоит мониторить)
BLOCKED_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0"
]

# Минимальная длина заголовка события
MIN_TITLE_LENGTH = int(os.getenv("MIN_TITLE_LENGTH", "3"))

# Максимальная длина заголовка события
MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "200"))

# Поддерживаемые форматы изображений
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Настройки для обработки ошибок
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # секунды

# Настройки для уведомлений
NOTIFICATION_SETTINGS = {{
    "enable_images": os.getenv("ENABLE_IMAGES", "true").lower() == "true",
    "enable_venue_info": os.getenv("ENABLE_VENUE_INFO", "true").lower() == "true",
    "enable_price_info": os.getenv("ENABLE_PRICE_INFO", "true").lower() == "true",
    "enable_date_info": os.getenv("ENABLE_DATE_INFO", "true").lower() == "true"
}}
"""
            
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            await update.message.reply_text(f"""
✅ Конфигурация обновлена для домена: {domain}

🔧 Настройки:
• Селектор событий: {event_selector}
• Селектор заголовка: {title_selector or 'по умолчанию'}
• Селектор даты: {date_selector or 'по умолчанию'}

🧪 Теперь протестируйте парсинг командой:
/test https://{domain}/anons
            """)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка сохранения конфигурации: {str(e)}")
    
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик сообщений с URL"""
        url = update.message.text.strip()
        user_id = update.effective_user.id
        
        if not self.is_valid_url(url):
            await update.message.reply_text("❌ Неверный формат ссылки. Пожалуйста, укажите корректный URL.")
            return
        
        # Проверяем, не отслеживается ли уже эта ссылка
        if url in self.monitored_urls:
            await update.message.reply_text("⚠️ Эта ссылка уже отслеживается!")
            return
        
        # Добавляем новую ссылку для мониторинга
        self.monitored_urls[url] = MonitoredUrl(
            url=url,
            user_id=user_id,
            last_check=datetime.now().isoformat(),
            last_hash="",
            events=[]
        )
        
        self.save_data()
        
        await update.message.reply_text(f"✅ Ссылка добавлена для мониторинга!\n🔗 {url}\n\nБот будет проверять обновления каждые 10 минут.")
    
    def is_valid_url(self, url: str) -> bool:
        """Проверка валидности URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def parse_events_from_page(self, url: str) -> List[ConcertEvent]:
        """Парсинг событий со страницы"""
        try:
            headers = {'User-Agent': USER_AGENT}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=HTTP_TIMEOUT, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка загрузки страницы {url}: статус {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    events = []
                    
                    # Проверяем есть ли специфичные селекторы для этого домена
                    domain = urlparse(url).netloc
                    site_config = SITE_SPECIFIC_CONFIGS.get(domain, {})
                    
                    elements = []
                    if site_config.get('event_selector'):
                        # Используем специфичный селектор для сайта
                        selector = site_config['event_selector']
                        elements = soup.select(selector)
                        logger.info(f"Используем специфичный селектор {selector} для {domain}: {len(elements)} элементов")
                    else:
                        # Используем универсальные селекторы
                        for selector in EVENT_SELECTORS:
                            elements = soup.select(selector)
                            if elements:
                                logger.info(f"Найдены элементы с селектором {selector}: {len(elements)}")
                                break
                    
                    if not elements:
                        # Если не найдены специфичные селекторы, ищем по общим паттернам
                        elements = soup.find_all(['div', 'article', 'section'], 
                                               class_=re.compile(r'(event|concert|show|card|item)', re.I))
                    
                    for element in elements[:MAX_ELEMENTS_TO_PARSE]:  # Ограничиваем количество для производительности
                        event = self.extract_event_data(element, url)
                        if event and event.title:
                            events.append(event)
                    
                    logger.info(f"Найдено событий на {url}: {len(events)}")
                    return events
                    
        except Exception as e:
            logger.error(f"Ошибка парсинга страницы {url}: {e}")
            return []
    
    def extract_event_data(self, element, base_url: str) -> Optional[ConcertEvent]:
        """Извлечение данных о событии из HTML элемента"""
        try:
            # Проверяем есть ли специфичные селекторы для этого домена
            domain = urlparse(base_url).netloc
            site_config = SITE_SPECIFIC_CONFIGS.get(domain, {})
            
            # Поиск заголовка
            title = None
            if site_config.get('title_selector'):
                # Используем специфичный селектор
                title_elem = element.select_one(site_config['title_selector'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            else:
                # Используем универсальные селекторы
                for selector in TITLE_SELECTORS:
                    title_elem = element.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
            
            if not title:
                # Пробуем найти текст в самом элементе
                title = element.get_text(strip=True)[:100]  # Ограничиваем длину
            
            # Поиск ссылки
            link_elem = element.find('a')
            event_url = None
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                event_url = urljoin(base_url, href)
            
            # Поиск даты
            date_text = None
            if site_config.get('date_selector'):
                # Используем специфичный селектор
                date_elem = element.select_one(site_config['date_selector'])
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
            else:
                # Используем универсальные селекторы
                for selector in DATE_SELECTORS:
                    date_elem = element.select_one(selector)
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        break
            
            # Поиск изображения
            img_elem = element.find('img')
            image_url = None
            if img_elem and img_elem.get('src'):
                src = img_elem.get('src')
                image_url = urljoin(base_url, src)
            
            # Поиск места проведения
            venue = None
            for selector in VENUE_SELECTORS:
                venue_elem = element.select_one(selector)
                if venue_elem:
                    venue = venue_elem.get_text(strip=True)
                    break
            
            # Поиск цены
            price = None
            for selector in PRICE_SELECTORS:
                price_elem = element.select_one(selector)
                if price_elem:
                    price = price_elem.get_text(strip=True)
                    break
            
            if title and MIN_TITLE_LENGTH <= len(title) <= MAX_TITLE_LENGTH:  # Проверяем длину заголовка
                return ConcertEvent(
                    title=title,
                    date=date_text or "Дата не указана",
                    url=event_url or base_url,
                    image_url=image_url,
                    venue=venue,
                    price=price
                )
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных события: {e}")
        
        return None
    
    def get_page_hash(self, events: List[ConcertEvent]) -> str:
        """Получение хэша страницы для определения изменений"""
        if not events:
            return ""
        
        # Создаем строку из всех событий для хэширования
        events_str = "|".join([f"{event.title}|{event.date}|{event.url}" for event in events])
        return hashlib.md5(events_str.encode('utf-8')).hexdigest()
    
    async def check_url_for_updates(self, url: str, monitored: MonitoredUrl, application):
        """Проверка URL на обновления"""
        try:
            logger.info(f"Проверка обновлений для {url}")
            
            # Парсим события
            current_events = await self.parse_events_from_page(url)
            current_hash = self.get_page_hash(current_events)
            
            # Проверяем, есть ли изменения
            if current_hash != monitored.last_hash:
                logger.info(f"Обнаружены изменения на {url}")
                
                # Определяем новые события
                old_event_hashes = self.events_cache.get(url, set())
                new_events = []
                
                for event in current_events:
                    event_hash = hashlib.md5(f"{event.title}|{event.date}".encode('utf-8')).hexdigest()
                    if event_hash not in old_event_hashes:
                        new_events.append(event)
                        old_event_hashes.add(event_hash)
                
                # Обновляем кэш
                self.events_cache[url] = old_event_hashes
                
                # Отправляем уведомления о новых событиях
                if new_events:
                    await self.send_new_events_notification(monitored.user_id, url, new_events, application)
                
                # Обновляем данные
                monitored.last_check = datetime.now().isoformat()
                monitored.last_hash = current_hash
                monitored.events = current_events
                
                self.save_data()
            else:
                logger.info(f"Изменений на {url} не обнаружено")
                # Обновляем время последней проверки
                monitored.last_check = datetime.now().isoformat()
                self.save_data()
                
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений для {url}: {e}")
    
    async def send_new_events_notification(self, user_id: int, url: str, new_events: List[ConcertEvent], application):
        """Отправка уведомления о новых событиях"""
        try:
            message_text = f"🎵 Новые события на сайте!\n🔗 {url}\n\n"
            
            for i, event in enumerate(new_events[:MAX_EVENTS_PER_NOTIFICATION], 1):  # Ограничиваем количество событий
                message_text += f"📅 {event.title}\n"
                message_text += f"📆 {event.date}\n"
                if event.venue:
                    message_text += f"📍 {event.venue}\n"
                if event.price:
                    message_text += f"💰 {event.price}\n"
                message_text += f"🔗 {event.url}\n\n"
            
            if len(new_events) > MAX_EVENTS_PER_NOTIFICATION:
                message_text += f"... и ещё {len(new_events) - MAX_EVENTS_PER_NOTIFICATION} событий"
            
            await application.bot.send_message(chat_id=user_id, text=message_text)
            
            # Отправляем изображения отдельными сообщениями
            if NOTIFICATION_SETTINGS["enable_images"]:
                for event in new_events[:MAX_IMAGES_PER_NOTIFICATION]:  # Ограничиваем количество изображений
                    if event.image_url:
                        try:
                            await application.bot.send_photo(
                                chat_id=user_id,
                                photo=event.image_url,
                                caption=f"🎵 {event.title}"
                            )
                        except Exception as e:
                            logger.error(f"Ошибка отправки изображения {event.image_url}: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
    
    async def monitoring_task(self, application):
        """Задача мониторинга"""
        while True:
            try:
                logger.info("Начало цикла мониторинга")
                
                if self.monitored_urls:
                    # Проверяем все отслеживаемые URL
                    tasks = []
                    for url, monitored in self.monitored_urls.items():
                        task = self.check_url_for_updates(url, monitored, application)
                        tasks.append(task)
                    
                    # Выполняем проверки параллельно
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                logger.info("Цикл мониторинга завершен")
                
            except Exception as e:
                logger.error(f"Ошибка в задаче мониторинга: {e}")
            
            # Ждем до следующей проверки
            await asyncio.sleep(MONITORING_INTERVAL)
    
    def run(self):
        """Запуск бота"""
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("add", self.add_url_command))
        application.add_handler(CommandHandler("list", self.list_urls_command))
        application.add_handler(CommandHandler("remove", self.remove_url_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("scan", self.scan_command))
        application.add_handler(CommandHandler("test", self.test_command))
        application.add_handler(CommandHandler("logs", self.logs_command))
        application.add_handler(CommandHandler("analyze", self.analyze_command))
        application.add_handler(CommandHandler("config", self.config_command))
        
        # Добавляем обработчик сообщений с URL
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url_message))
        
        # Запускаем мониторинг в фоне через JobQueue
        def start_monitoring(context):
            asyncio.create_task(self.monitoring_task(application))
        
        application.job_queue.run_once(start_monitoring, when=1)
        
        # Запускаем бота
        logger.info("Запуск бота...")
        application.run_polling()

if __name__ == "__main__":
    bot = ConcertMonitorBot()
    bot.run()