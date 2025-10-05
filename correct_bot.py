#!/usr/bin/env python3
"""
Правильный бот согласно ТЗ - только уведомления при изменениях
"""

import asyncio
import logging
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict

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
MONITORING_INTERVAL = 600  # 10 минут
HTTP_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

@dataclass
class MonitoredUrl:
    url: str
    user_id: int
    last_check: str
    last_hash: str
    group_chat_id: Optional[int] = None

class CorrectBot:
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
                            last_check=url_data['last_check'],
                            last_hash=url_data['last_hash'],
                            group_chat_id=url_data.get('group_chat_id')
                        )
                logger.info(f"Загружено {len(self.monitored_urls)} ссылок для мониторинга")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    def save_data(self):
        try:
            data = {}
            for url, monitored in self.monitored_urls.items():
                data[url] = {
                    'url': monitored.url,
                    'user_id': monitored.user_id,
                    'last_check': monitored.last_check,
                    'last_hash': monitored.last_hash,
                    'group_chat_id': monitored.group_chat_id
                }
            
            with open('monitored_urls.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("""
🎵 Бот мониторинга концертных площадок

📋 Команды:
/ping - проверка работы
/add <ссылка> - добавить ссылку для мониторинга
/list - список ваших ссылок
/status - статус мониторинга
/setgroup - настроить групповые уведомления

Просто отправьте ссылку на страницу с событиями!
            """)
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
    
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("🏓 Pong! Бот работает!")
        except Exception as e:
            logger.error(f"Ошибка в ping_command: {e}")
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await update.message.reply_text("❌ Укажите ссылку: /add https://example.com/events")
                return
            
            url = context.args[0]
            user_id = update.effective_user.id
            
            if url in self.monitored_urls:
                await update.message.reply_text("❌ Ссылка уже отслеживается!")
                return
            
            self.monitored_urls[url] = MonitoredUrl(
                url=url,
                user_id=user_id,
                last_check=datetime.now().isoformat(),
                last_hash=""
            )
            
            self.save_data()
            await update.message.reply_text(f"✅ Ссылка добавлена для мониторинга: {url}")
        except Exception as e:
            logger.error(f"Ошибка в add_command: {e}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
            
            if not user_urls:
                await update.message.reply_text("❌ У вас нет отслеживаемых ссылок")
                return
            
            text = "📋 Ваши отслеживаемые ссылки:\n\n"
            for i, url in enumerate(user_urls, 1):
                text += f"{i}. {url}\n"
            
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Ошибка в list_command: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            total_urls = len(self.monitored_urls)
            user_id = update.effective_user.id
            user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
            
            text = f"""
📊 Статус мониторинга:

🔗 Всего отслеживаемых ссылок: {total_urls}
👤 Ваших ссылок: {len(user_urls)}
⏰ Интервал проверки: {MONITORING_INTERVAL // 60} минут
🔄 Текущее время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

{'✅ Мониторинг активен' if total_urls > 0 else '⏸️ Мониторинг неактивен'}
            """
            
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Ошибка в status_command: {e}")
    
    async def setgroup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            if update.effective_chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ Эта команда работает только в групповых чатах!")
                return
            
            user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
            
            if not user_urls:
                await update.message.reply_text("❌ У вас нет отслеживаемых ссылок!")
                return
            
            for url in user_urls:
                self.monitored_urls[url].group_chat_id = chat_id
            
            self.save_data()
            await update.message.reply_text(f"""
✅ Групповые уведомления настроены!

👥 Чат: {update.effective_chat.title}
🔗 Ссылок: {len(user_urls)}
📱 Уведомления будут приходить в этот чат
            """)
        except Exception as e:
            logger.error(f"Ошибка в setgroup_command: {e}")
    
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            text = update.message.text
            user_id = update.effective_user.id
            
            if text.startswith('http'):
                if text in self.monitored_urls:
                    await update.message.reply_text("❌ Ссылка уже отслеживается!")
                    return
                
                self.monitored_urls[text] = MonitoredUrl(
                    url=text,
                    user_id=user_id,
                    last_check=datetime.now().isoformat(),
                    last_hash=""
                )
                
                self.save_data()
                await update.message.reply_text(f"✅ Ссылка добавлена для мониторинга: {text}")
        except Exception as e:
            logger.error(f"Ошибка в handle_url_message: {e}")
    
    async def parse_events(self, url: str, content: str) -> list:
        """Парсинг событий с конкретной страницы"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            events = []
            
            # Селекторы для поиска событий
            selectors = [
                '[class*="event"]',
                '[class*="item"]', 
                '[class*="card"]',
                '[class*="show"]',
                '.event',
                '.item',
                '.card',
                '.show'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Найдены элементы с селектором {selector}: {len(elements)}")
                    
                    for element in elements[:10]:  # Ограничиваем количество
                        try:
                            # Извлекаем заголовок
                            title = ""
                            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.name', 'a']
                            for title_sel in title_selectors:
                                title_elem = element.select_one(title_sel)
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    break
                            
                            if not title:
                                title = element.get_text(strip=True)[:100]
                            
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
                            
                            # Фильтруем пустые события
                            if title and len(title) > 3:
                                events.append({
                                    'title': title,
                                    'date': date or "Дата не указана",
                                    'url': event_url
                                })
                        
                        except Exception as e:
                            logger.error(f"Ошибка парсинга элемента: {e}")
                            continue
                    
                    break  # Используем первый найденный селектор
            
            return events
        except Exception as e:
            logger.error(f"Ошибка парсинга событий: {e}")
            return []
    
    async def check_url(self, url: str, monitored: MonitoredUrl, application):
        """Проверка конкретной ссылки на изменения"""
        try:
            logger.info(f"Проверка {url}")
            
            timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={'User-Agent': USER_AGENT}) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка {url}: {response.status}")
                        return
                    
                    content = await response.text()
                    current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                    
                    # Проверяем, есть ли изменения
                    if current_hash != monitored.last_hash:
                        logger.info(f"Обнаружены изменения на {url}")
                        
                        # Парсим события
                        events = await self.parse_events(url, content)
                        
                        if events:
                            # Формируем сообщение с событиями
                            message = f"🎵 Новые события на сайте!\n🔗 {url}\n\n"
                            
                            for i, event in enumerate(events[:5], 1):  # Показываем до 5 событий
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
                        await application.bot.send_message(chat_id=chat_id, text=message)
                        
                        # Обновляем данные
                        monitored.last_hash = current_hash
                        monitored.last_check = datetime.now().isoformat()
                        self.save_data()
                    else:
                        logger.info(f"Изменений на {url} нет")
        
        except Exception as e:
            logger.error(f"Ошибка проверки {url}: {e}")
    
    async def monitoring_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Задача мониторинга - проверяет только при изменениях"""
        try:
            logger.info("Начало цикла мониторинга")
            
            if self.monitored_urls:
                # Проверяем все ссылки последовательно
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
            first=10  # Запуск через 10 секунд
        )
        
        logger.info("🎵 Запуск правильного бота...")
        application.run_polling()

if __name__ == "__main__":
    bot = CorrectBot()
    bot.run()