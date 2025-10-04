#!/usr/bin/env python3
"""
Надежный бот для мониторинга концертных площадок
"""

import asyncio
import logging
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import aiohttp
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "7711964415:AAF0tp9uhybhTZ7gPEGLNnpE6TxgvAElYzU"
MONITORING_INTERVAL = 600  # 10 минут
HTTP_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

@dataclass
class ConcertEvent:
    title: str
    date: str
    url: str

@dataclass
class MonitoredUrl:
    url: str
    user_id: int
    last_check: str
    last_hash: str
    events: List[ConcertEvent]
    group_chat_id: Optional[int] = None

class ReliableConcertBot:
    def __init__(self):
        self.monitored_urls: Dict[str, MonitoredUrl] = {}
        self.events_cache: Dict[str, set] = {}
        self.load_data()
        self.is_running = True
    
    def load_data(self):
        """Загрузка данных"""
        try:
            if os.path.exists('monitored_urls.json'):
                with open('monitored_urls.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for url, url_data in data.items():
                        events = [ConcertEvent(**event) for event in url_data.get('events', [])]
                        self.monitored_urls[url] = MonitoredUrl(
                            url=url_data['url'],
                            user_id=url_data['user_id'],
                            last_check=url_data['last_check'],
                            last_hash=url_data['last_hash'],
                            events=events,
                            group_chat_id=url_data.get('group_chat_id')
                        )
            
            if os.path.exists('events_cache.json'):
                with open('events_cache.json', 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.events_cache = {url: set(hashes) for url, hashes in cache_data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    def save_data(self):
        """Сохранение данных"""
        try:
            data = {}
            for url, monitored in self.monitored_urls.items():
                data[url] = {
                    'url': monitored.url,
                    'user_id': monitored.user_id,
                    'last_check': monitored.last_check,
                    'last_hash': monitored.last_hash,
                    'events': [asdict(event) for event in monitored.events],
                    'group_chat_id': monitored.group_chat_id
                }
            
            with open('monitored_urls.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            cache_data = {url: list(hashes) for url, hashes in self.events_cache.items()}
            with open('events_cache.json', 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        await update.message.reply_text("""
🎵 Надежный бот мониторинга концертов!

📋 Команды:
/ping - проверка работы
/add <ссылка> - добавить ссылку
/list - список ссылок
/status - статус
/setgroup - групповые уведомления

Просто отправьте ссылку!
        """)
    
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /ping"""
        await update.message.reply_text("🏓 Pong! Бот работает стабильно!")
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add"""
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
            last_check=datetime.now().isoformat(),
            last_hash="",
            events=[]
        )
        
        self.save_data()
        await update.message.reply_text(f"✅ Ссылка добавлена: {url}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /list"""
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
        """Команда /status"""
        total_urls = len(self.monitored_urls)
        user_id = update.effective_user.id
        user_urls = [url for url, data in self.monitored_urls.items() if data.user_id == user_id]
        
        text = f"""
📊 Статус мониторинга:

🔗 Всего ссылок: {total_urls}
👤 Ваших ссылок: {len(user_urls)}
⏰ Интервал: {MONITORING_INTERVAL // 60} минут
🔄 Время: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}

{'✅ Мониторинг активен' if total_urls > 0 else '⏸️ Мониторинг неактивен'}
        """
        
        await update.message.reply_text(text)
    
    async def setgroup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /setgroup"""
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
        await update.message.reply_text(f"""
✅ Групповые уведомления настроены!

👥 Чат: {update.effective_chat.title}
🔗 Ссылок: {len(user_urls)}
📱 Уведомления в этот чат
        """)
    
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка URL"""
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
                last_hash="",
                events=[]
            )
            
            self.save_data()
            await update.message.reply_text(f"✅ Ссылка добавлена: {text}")
    
    async def check_url_simple(self, url: str, monitored: MonitoredUrl, application):
        """Простая проверка ссылки"""
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
                    
                    if current_hash != monitored.last_hash:
                        logger.info(f"Изменения на {url}")
                        
                        chat_id = monitored.group_chat_id if monitored.group_chat_id else monitored.user_id
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"🔄 Обновления на сайте!\n🔗 {url}"
                        )
                        
                        monitored.last_hash = current_hash
                        monitored.last_check = datetime.now().isoformat()
                        self.save_data()
                    else:
                        logger.info(f"Изменений на {url} нет")
        
        except Exception as e:
            logger.error(f"Ошибка проверки {url}: {e}")
    
    async def monitoring_loop(self, application):
        """Основной цикл мониторинга"""
        logger.info("🚀 Запуск мониторинга")
        
        while self.is_running:
            try:
                logger.info("Начало цикла мониторинга")
                
                if self.monitored_urls:
                    # Проверяем все ссылки последовательно (более надежно)
                    for url, monitored in self.monitored_urls.items():
                        try:
                            await asyncio.wait_for(
                                self.check_url_simple(url, monitored, application),
                                timeout=30
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Таймаут для {url}")
                        except Exception as e:
                            logger.error(f"Ошибка для {url}: {e}")
                
                logger.info("Цикл мониторинга завершен")
                
            except Exception as e:
                logger.error(f"Критическая ошибка в мониторинге: {e}")
            
            # Ждем до следующей проверки
            await asyncio.sleep(MONITORING_INTERVAL)
    
    async def run(self):
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
        
        # Запускаем мониторинг в фоне
        monitoring_task = asyncio.create_task(self.monitoring_loop(application))
        
        try:
            logger.info("🎵 Запуск надежного бота...")
            await application.run_polling()
        except KeyboardInterrupt:
            logger.info("Остановка бота...")
            self.is_running = False
            monitoring_task.cancel()
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            self.is_running = False

if __name__ == "__main__":
    bot = ReliableConcertBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")