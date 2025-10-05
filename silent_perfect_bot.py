#!/usr/bin/env python3
"""
Совершенно тихий бот - НИКОГДА не присылает уведомления при первом запуске
"""

import asyncio
import logging
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7711964415:AAF0tp9uhybhTZ7gPEGLNnpE6TxgvAElYzU"
MONITORING_INTERVAL = 300  # 5 минут
HTTP_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

@dataclass
class MonitoredUrl:
    url: str
    user_id: int
    last_events_hash: str
    is_initialized: bool = False  # Флаг инициализации
    group_chat_id: Optional[int] = None

class SilentPerfectBot:
    def __init__(self):
        self.monitored_urls: Dict[str, MonitoredUrl] = {}
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists('monitored_urls.json'):
                with open('monitored_urls.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for url, url_data in data.items():
                        self.monitored_urls[url] = MonitoredUrl(
                            url=url_data['url'],
                            user_id=url_data['user_id'],
                            last_events_hash=url_data.get('last_events_hash', ''),
                            is_initialized=url_data.get('is_initialized', False),
                            group_chat_id=url_data.get('group_chat_id')
                        )
                logger.info(f"Загружено {len(self.monitored_urls)} ссылок")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    def save_data(self):
        try:
            data = {}
            for url, monitored in self.monitored_urls.items():
                data[url] = {
                    'url': monitored.url,
                    'user_id': monitored.user_id,
                    'last_events_hash': monitored.last_events_hash,
                    'is_initialized': monitored.is_initialized,
                    'group_chat_id': monitored.group_chat_id
                }
            
            with open('monitored_urls.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("""
🎵 Бот мониторинга концертных площадок

📋 Команды:
/ping - проверка работы
/add <ссылка> - добавить ссылку
/list - список ссылок
/status - статус
/setgroup - настроить группу

Просто отправьте ссылку!
        """)
    
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🏓 Pong! Работаю!")
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите ссылку: /add https://example.com")
            return
        
        url = context.args[0]
        user_id = update.effective_user.id
        
        if url in self.monitored_urls:
            await update.message.reply_text("❌ Ссылка уже отслеживается!")
            return
        
        self.monitored_urls[url] = MonitoredUrl(
            url=url,
            user_id=user_id,
            last_events_hash="",
            is_initialized=False
        )
        
        self.save_data()
        await update.message.reply_text(f"✅ Ссылка добавлена: {url}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        if not user_urls:
            await update.message.reply_text("❌ Нет отслеживаемых ссылок")
            return
        
        text = "📋 Ваши ссылки:\n\n"
        for i, url in enumerate(user_urls, 1):
            text += f"{i}. {url}\n"
        
        await update.message.reply_text(text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        total_urls = len(self.monitored_urls)
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        text = f"""
📊 Статус:

🔗 Всего ссылок: {total_urls}
👤 Ваших ссылок: {len(user_urls)}
⏰ Интервал: {MONITORING_INTERVAL // 60} минут
🔄 Время: {datetime.now().strftime('%H:%M:%S')}

{'✅ Активен' if total_urls > 0 else '⏸️ Неактивен'}
        """
        
        await update.message.reply_text(text)
    
    async def setgroup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        if update.effective_chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("❌ Только в группах!")
            return
        
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        if not user_urls:
            await update.message.reply_text("❌ Нет ссылок!")
            return
        
        for url in user_urls:
            self.monitored_urls[url].group_chat_id = chat_id
        
        self.save_data()
        await update.message.reply_text(f"✅ Группа настроена! Ссылок: {len(user_urls)}")
    
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        user_id = update.effective_user.id
        
        if text.startswith('http'):
            if text in self.monitored_urls:
                await update.message.reply_text("❌ Ссылка уже отслеживается!")
                return
            
            self.monitored_urls[text] = MonitoredUrl(
                url=text,
                user_id=user_id,
                last_events_hash="",
                is_initialized=False
            )
            
            self.save_data()
            await update.message.reply_text(f"✅ Ссылка добавлена: {text}")
    
    def is_valid_event(self, title: str) -> bool:
        """Проверяет, является ли заголовок валидным событием"""
        if len(title.strip()) < 5:
            return False
        
        # Ключевые слова для концертных событий
        event_keywords = [
            'концерт', 'concert', 'шоу', 'show', 'спектакль', 'performance',
            'фестиваль', 'festival', 'вечеринка', 'party', 'дискотека',
            'диско', 'disco', 'клуб', 'club', 'зал', 'hall', 'арена',
            'arena', 'театр', 'theater', 'theatre', 'цирк', 'circus',
            'выставка', 'exhibition', 'мероприятие', 'event', 'билет',
            'ticket', 'продажа', 'sale', 'афиша', 'poster', 'гастроли',
            'tour', 'тур', 'концертная', 'музыка', 'music', 'танцы',
            'dance', 'балет', 'ballet', 'опера', 'opera', 'симфония',
            'symphony', 'джаз', 'jazz', 'рок', 'rock', 'поп', 'pop',
            'классика', 'classical', 'электроника', 'electronic'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in event_keywords)
    
    async def extract_events(self, url: str, content: str) -> list:
        """Извлекает только концертные события"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            events = []
            
            # Селекторы для поиска событий
            selectors = [
                '[class*="event"]', '[class*="item"]', '[class*="card"]',
                '[class*="show"]', '[class*="concert"]', '[class*="performance"]',
                '.event', '.item', '.card', '.show', '.concert', '.performance'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Найдены элементы с селектором {selector}: {len(elements)}")
                    
                    for element in elements[:20]:
                        try:
                            # Извлекаем заголовок
                            title = ""
                            title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', '.title', '.name', 'a']
                            for title_sel in title_selectors:
                                title_elem = element.select_one(title_sel)
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    break
                            
                            if not title:
                                title = element.get_text(strip=True)[:200]
                            
                            # Проверяем валидность события
                            if self.is_valid_event(title):
                                # Извлекаем дату
                                date = ""
                                date_selectors = ['.date', '.time', '[class*="date"]', '[class*="time"]']
                                for date_sel in date_selectors:
                                    date_elem = element.select_one(date_sel)
                                    if date_elem:
                                        date = date_elem.get_text(strip=True)
                                        break
                                
                                # Извлекаем ссылку
                                event_url = url
                                link_elem = element.select_one('a')
                                if link_elem and link_elem.get('href'):
                                    href = link_elem.get('href')
                                    if href.startswith('http'):
                                        event_url = href
                                    elif href.startswith('/'):
                                        from urllib.parse import urljoin
                                        event_url = urljoin(url, href)
                                
                                events.append({
                                    'title': title,
                                    'date': date or "Дата не указана",
                                    'url': event_url
                                })
                        
                        except Exception as e:
                            logger.error(f"Ошибка парсинга элемента: {e}")
                            continue
                    
                    break
            
            logger.info(f"Извлечено валидных событий: {len(events)}")
            return events
            
        except Exception as e:
            logger.error(f"Ошибка извлечения событий: {e}")
            return []
    
    def get_events_hash(self, events: list) -> str:
        """Создает хеш из событий для сравнения"""
        if not events:
            return ""
        
        sorted_events = sorted(events, key=lambda x: x['title'])
        events_str = "|".join([f"{e['title']}|{e['date']}" for e in sorted_events])
        return hashlib.md5(events_str.encode('utf-8')).hexdigest()
    
    async def check_url(self, url: str, monitored: MonitoredUrl, application):
        """Проверка ссылки на НОВЫЕ события"""
        try:
            logger.info(f"Проверка {url}")
            
            timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={'User-Agent': USER_AGENT}) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка {url}: {response.status}")
                        return
                    
                    content = await response.text()
                    
                    # Извлекаем только концертные события
                    events = await self.extract_events(url, content)
                    current_events_hash = self.get_events_hash(events)
                    
                    # Если это первая проверка - просто сохраняем хеш, НЕ отправляем уведомления
                    if not monitored.is_initialized:
                        logger.info(f"Инициализация {url} - сохраняем хеш без уведомлений")
                        monitored.last_events_hash = current_events_hash
                        monitored.is_initialized = True
                        self.save_data()
                        return
                    
                    # Проверяем, есть ли НОВЫЕ события
                    if current_events_hash != monitored.last_events_hash and current_events_hash:
                        logger.info(f"Обнаружены НОВЫЕ события на {url}")
                        
                        if events:
                            # Формируем сообщение с событиями
                            message = f"🎵 Новые события на сайте!\n🔗 {url}\n\n"
                            
                            for i, event in enumerate(events[:5], 1):
                                message += f"📅 {event['title']}\n"
                                if event['date'] != "Дата не указана":
                                    message += f"   🕐 {event['date']}\n"
                                if event['url'] != url:
                                    message += f"   🔗 {event['url']}\n"
                                message += "\n"
                            
                            if len(events) > 5:
                                message += f"... и ещё {len(events) - 5} событий"
                        else:
                            message = f"🔄 Обновления на сайте!\n🔗 {url}\n\n(События не найдены)"
                        
                        # Отправляем уведомление
                        chat_id = monitored.group_chat_id if monitored.group_chat_id else monitored.user_id
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=message)
                            logger.info(f"Уведомление отправлено для {url}")
                        except Exception as e:
                            logger.error(f"Ошибка отправки: {e}")
                        
                        # Обновляем хеш событий
                        monitored.last_events_hash = current_events_hash
                        self.save_data()
                    else:
                        logger.info(f"Новых событий на {url} нет")
        
        except Exception as e:
            logger.error(f"Ошибка проверки {url}: {e}")
    
    async def monitoring_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Задача мониторинга - проверяет только НОВЫЕ события"""
        try:
            logger.info("Начало цикла мониторинга")
            
            if self.monitored_urls:
                for url, monitored in self.monitored_urls.items():
                    try:
                        await asyncio.wait_for(
                            self.check_url(url, monitored, context.application),
                            timeout=30
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Таймаут для {url}")
                    except Exception as e:
                        logger.error(f"Ошибка для {url}: {e}")
            
            logger.info("Цикл мониторинга завершен")
        except Exception as e:
            logger.error(f"Ошибка в мониторинге: {e}")
    
    def run(self):
        """Запуск бота"""
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("ping", self.ping_command))
        application.add_handler(CommandHandler("add", self.add_command))
        application.add_handler(CommandHandler("list", self.list_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("setgroup", self.setgroup_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url_message))
        
        # Запускаем мониторинг через JobQueue
        application.job_queue.run_repeating(
            self.monitoring_job,
            interval=MONITORING_INTERVAL,
            first=10
        )
        
        logger.info("🎵 Запуск совершенно тихого бота...")
        application.run_polling()

if __name__ == "__main__":
    bot = SilentPerfectBot()
    bot.run()