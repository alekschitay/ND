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

📋 Доступные команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/help - показать справку

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

⚙️ Команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/status - показать статус мониторинга

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
        user_urls = len([url for url, data in self.monitored_urls.items() if data.user_id == user_id])
        
        status_text = f"""
📊 Статус мониторинга:

🔗 Всего отслеживаемых ссылок: {total_urls}
👤 Ваших ссылок: {user_urls}
⏰ Интервал проверки: 10 минут
🔄 Последняя проверка: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}

{'✅ Мониторинг активен' if total_urls > 0 else '⏸️ Мониторинг неактивен'}
        """
        
        await update.message.reply_text(status_text)
    
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
                    
                    # Используем селекторы из конфигурации
                    elements = []
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
            # Поиск заголовка
            title = None
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
        
        # Добавляем обработчик сообщений с URL
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url_message))
        
        # Запускаем мониторинг в фоне
        application.job_queue.run_once(
            lambda context: asyncio.create_task(self.monitoring_task(application)),
            when=1
        )
        
        # Запускаем бота
        logger.info("Запуск бота...")
        application.run_polling()

if __name__ == "__main__":
    bot = ConcertMonitorBot()
    bot.run()