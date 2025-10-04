"""
Telegram бот для мониторинга концертных площадок
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

from config_new import BOT_TOKEN, CHECK_INTERVAL_MINUTES
from database_new import Database
from monitor_new import PageMonitor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ConcertMonitorBot:
    def __init__(self):
        self.db = Database()
        self.monitor = PageMonitor()
        self.application = None
    
    def _is_valid_url(self, url: str) -> bool:
        """Проверка валидности URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Извлечение домена из URL"""
        try:
            return urlparse(url).netloc
        except:
            return url
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Добавляем пользователя в базу
        await self.db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = """
🎵 Добро пожаловать в Concert Monitor Bot!

Я помогу вам отслеживать обновления на сайтах концертных площадок.

📋 Доступные команды:
/start - Начать работу
/add - Добавить страницу для мониторинга
/list - Показать отслеживаемые страницы
/remove - Удалить страницу из мониторинга
/test - Тестировать парсинг страницы
/images - Тестировать извлечение изображений-афиш
/sites - Показать поддерживаемые сайты
/status - Проверить статус мониторинга
/check - Принудительная проверка страниц
/simulate - Симуляция нового события
/help - Помощь

🔗 Чтобы добавить страницу для мониторинга, используйте команду /add или просто отправьте ссылку на страницу.

🖼️ Для страниц с графическими афишами используйте команду /images для тестирования.
📊 Используйте /status для проверки работы мониторинга.
🔍 Используйте /check для принудительной проверки всех страниц.
        """
        
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 Справка по командам:

🔗 Управление страницами:
/add - Добавить страницу для мониторинга
/list - Показать отслеживаемые страницы
/remove - Удалить страницу из мониторинга

🔍 Тестирование:
/test <URL или домен> - Тестировать парсинг страницы
/images <URL или домен> - Тестировать извлечение изображений-афиш

📊 Мониторинг:
/status - Проверить статус мониторинга
/check - Принудительная проверка страниц
/simulate - Симуляция нового события

ℹ️ Информация:
/sites - Показать поддерживаемые сайты
/help - Показать эту справку

💡 Примеры использования:
/test viagogo.com
/images memobar.ru
/add https://example.com/events
        """
        await update.message.reply_text(help_text)
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /add"""
        if not context.args:
            await update.message.reply_text(
                "➕ Использование: /add <URL или домен>\n\n"
                "Примеры:\n"
                "/add https://example.com/events\n"
                "/add example.com\n"
                "/add viagogo.com"
            )
            return
        
        url = context.args[0]
        
        # Если это не полный URL, добавляем протокол
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if not self._is_valid_url(url):
            await update.message.reply_text("❌ Пожалуйста, укажите корректную ссылку.")
            return
        
        user_id = update.effective_user.id
        site_name = self._extract_domain(url)
        
        try:
            # Проверяем, не добавлена ли уже эта страница
            pages = await self.db.get_user_pages(user_id)
            for page in pages:
                if page['url'] == url:
                    await update.message.reply_text("⚠️ Эта страница уже отслеживается!")
                    return
            
            # Добавляем страницу
            await self.db.add_monitored_page(user_id, url, site_name)
            await update.message.reply_text(
                f"✅ Страница добавлена для мониторинга!\n\n"
                f"🔗 {site_name}\n"
                f"📅 Бот будет проверять обновления каждые {CHECK_INTERVAL_MINUTES} минут."
            )
            
        except Exception as e:
            logger.error(f"Ошибка добавления страницы: {e}")
            await update.message.reply_text("❌ Ошибка добавления страницы.")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /list"""
        user_id = update.effective_user.id
        
        try:
            pages = await self.db.get_user_pages(user_id)
            
            if not pages:
                await update.message.reply_text(
                    "📝 У вас пока нет отслеживаемых страниц.\n\n"
                    "Используйте /add для добавления страницы или просто отправьте ссылку."
                )
                return
            
            text = "📋 Ваши отслеживаемые страницы:\n\n"
            
            for i, page in enumerate(pages, 1):
                site_name = page['site_name'] or self._extract_domain(page['url'])
                last_check = page.get('last_check', 'Никогда')
                
                text += f"{i}. 🔗 {site_name}\n"
                text += f"   URL: {page['url']}\n"
                text += f"   📅 Последняя проверка: {last_check}\n\n"
            
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка страниц: {e}")
            await update.message.reply_text("❌ Ошибка получения списка страниц.")
    
    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /remove"""
        user_id = update.effective_user.id
        
        try:
            pages = await self.db.get_user_pages(user_id)
            
            if not pages:
                await update.message.reply_text("📝 У вас нет отслеживаемых страниц.")
                return
            
            if len(pages) == 1:
                # Если только одна страница, удаляем сразу
                await self.db.remove_page(pages[0]['id'], user_id)
                await update.message.reply_text("✅ Страница удалена из мониторинга.")
                return
            
            # Создаем клавиатуру для выбора страницы
            keyboard = []
            for i, page in enumerate(pages):
                site_name = page['site_name'] or self._extract_domain(page['url'])
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {site_name}",
                    callback_data=f"remove_{page['id']}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🗑️ Выберите страницу для удаления:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка удаления страницы: {e}")
            await update.message.reply_text("❌ Ошибка удаления страницы.")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test для тестирования парсинга"""
        if not context.args:
            await update.message.reply_text(
                "🔍 Использование: /test <URL или домен>\n\n"
                "Примеры:\n"
                "/test https://example.com/events\n"
                "/test example.com\n"
                "/test viagogo.com"
            )
            return
        
        url = context.args[0]
        
        # Если это не полный URL, добавляем протокол
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if not self._is_valid_url(url):
            await update.message.reply_text("❌ Пожалуйста, укажите корректную ссылку.")
            return
        
        await update.message.reply_text("🔍 Тестирую парсинг страницы...")
        
        try:
            result = await self.monitor.test_page_parsing(url)
            
            if 'error' in result:
                await update.message.reply_text(f"❌ Ошибка: {result['error']}")
                return
            
            text = f"📊 Результаты тестирования:\n\n"
            text += f"🔗 URL: {result['url']}\n"
            text += f"📄 Размер страницы: {result['content_length']} символов\n"
            text += f"🎵 Найдено событий: {result['events_found']}\n\n"
            
            if result['events']:
                text += "📋 Примеры найденных событий:\n"
                for i, event in enumerate(result['events'], 1):
                    text += f"{i}. {event['title']}\n"
                    if event['date']:
                        text += f"   📅 {event['date']}\n"
                    if event['link']:
                        text += f"   🔗 {event['link']}\n"
                    if event.get('image_url'):
                        text += f"   🖼️ Изображение: {event['image_url'][:50]}...\n"
                    text += "\n"
                
                # Отправляем первое изображение как фото
                first_event = result['events'][0]
                if first_event.get('image_url'):
                    try:
                        await update.message.reply_photo(
                            photo=first_event['image_url'],
                            caption=f"🖼️ Пример изображения: {first_event['title']}"
                        )
                    except TelegramError as e:
                        logger.error(f"Ошибка отправки изображения: {e}")
                        text += f"⚠️ Не удалось отправить изображение: {str(e)}\n"
            else:
                text += "⚠️ События не найдены"
            
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Ошибка тестирования: {e}")
            await update.message.reply_text(f"❌ Ошибка тестирования: {str(e)}")
    
    async def images_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /images для тестирования извлечения изображений"""
        if not context.args:
            await update.message.reply_text(
                "🖼️ Использование: /images <URL или домен>\n\n"
                "Примеры:\n"
                "/images https://example.com/posters\n"
                "/images example.com\n"
                "/images memobar.ru\n\n"
                "Эта команда специально для страниц с графическими афишами."
            )
            return
        
        url = context.args[0]
        
        # Если это не полный URL, добавляем протокол
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if not self._is_valid_url(url):
            await update.message.reply_text("❌ Пожалуйста, укажите корректную ссылку.")
            return
        
        await update.message.reply_text("🖼️ Тестирую извлечение изображений...")
        
        try:
            # Загружаем страницу
            content = await self.monitor.fetch_page(url)
            if not content:
                await update.message.reply_text("❌ Не удалось загрузить страницу.")
                return
            
            # Извлекаем события
            events = self.monitor.extract_events_from_html(content, url)
            
            # Фильтруем события с изображениями
            image_events = [event for event in events if event.get('image_url')]
            
            text = f"🖼️ Результаты извлечения изображений:\n\n"
            text += f"🔗 URL: {url}\n"
            text += f"📄 Размер страницы: {len(content)} символов\n"
            text += f"🎵 Найдено событий: {len(events)}\n"
            text += f"🖼️ Событий с изображениями: {len(image_events)}\n\n"
            
            if image_events:
                text += "📋 Примеры изображений:\n"
                for i, event in enumerate(image_events[:3], 1):
                    text += f"{i}. {event['title']}\n"
                    text += f"   🖼️ {event['image_url']}\n\n"
                
                # Отправляем первое изображение как фото
                try:
                    await update.message.reply_photo(
                        photo=image_events[0]['image_url'],
                        caption=f"🖼️ {image_events[0]['title']}"
                    )
                except TelegramError as e:
                    logger.error(f"Ошибка отправки изображения: {e}")
                    text += f"⚠️ Не удалось отправить изображение: {str(e)}\n"
            else:
                text += "⚠️ Изображения не найдены"
            
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Ошибка тестирования изображений: {e}")
            await update.message.reply_text(f"❌ Ошибка тестирования изображений: {str(e)}")
    
    async def sites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /sites"""
        sites_text = """
🌐 Поддерживаемые сайты:

🎵 Концертные площадки:
• kremlinpalace.org - Кремлевский дворец
• livearena.ru - Live Arena
• vk-stadium.ru - ВТБ Арена
• zavarkalive.ru - Заварка Live

🎪 Фестивали и события:
• letolifefest.ru - Leto Life Fest
• crave.ru - Crave
• sohorooms.com - Soho Rooms

🖼️ Сайты с графическими афишами:
• memobar.ru - MemoBar (блок афиш)

🎫 Билетные операторы:
• viagogo.com - Viagogo

💡 Бот также может работать с другими сайтами концертных площадок!
        """
        await update.message.reply_text(sites_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status для проверки статуса мониторинга"""
        user_id = update.effective_user.id
        
        try:
            # Получаем отслеживаемые страницы пользователя
            pages = await self.db.get_user_pages(user_id)
            
            if not pages:
                await update.message.reply_text(
                    "📝 У вас пока нет отслеживаемых страниц.\n\n"
                    "Используйте /add для добавления страницы или просто отправьте ссылку."
                )
                return
            
            text = "📊 Статус мониторинга:\n\n"
            
            for page in pages:
                site_name = page['site_name'] or self._extract_domain(page['url'])
                last_check = page.get('last_check', 'Никогда')
                
                text += f"🔗 {site_name}\n"
                text += f"   URL: {page['url']}\n"
                text += f"   📅 Последняя проверка: {last_check}\n"
                text += f"   ✅ Статус: Активен\n\n"
            
            text += f"⏰ Интервал проверки: {CHECK_INTERVAL_MINUTES} минут\n"
            text += f"🤖 Бот работает и мониторит ваши страницы!\n\n"
            text += "💡 Когда на сайтах появятся новые события, вы получите уведомления."
            
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статуса: {str(e)}")
    
    async def simulate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /simulate для симуляции нового события"""
        user_id = update.effective_user.id
        
        try:
            # Получаем отслеживаемые страницы пользователя
            pages = await self.db.get_user_pages(user_id)
            
            if not pages:
                await update.message.reply_text(
                    "📝 У вас пока нет отслеживаемых страниц.\n\n"
                    "Используйте /add для добавления страницы."
                )
                return
            
            # Берем первую страницу для симуляции
            page = pages[0]
            site_name = page['site_name'] or self._extract_domain(page['url'])
            
            # Создаем тестовое событие
            test_event = {
                'title': '🎵 Тестовое событие (симуляция)',
                'date': '2024-01-01',
                'link': page['url'],
                'image_url': 'https://via.placeholder.com/400x300/FF6B6B/FFFFFF?text=Test+Event',
                'content_hash': 'test_simulation_' + str(user_id)
            }
            
            # Отправляем симуляцию
            await self.send_notification(user_id, page, [test_event])
            
            await update.message.reply_text(
                f"✅ Симуляция отправлена!\n\n"
                f"🔗 Сайт: {site_name}\n"
                f"📊 Это показывает, как будут выглядеть уведомления о новых событиях.\n\n"
                f"💡 Когда на реальных сайтах появятся новые события, вы получите такие же уведомления."
            )
            
        except Exception as e:
            logger.error(f"Ошибка симуляции: {e}")
            await update.message.reply_text(f"❌ Ошибка симуляции: {str(e)}")
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /check для принудительной проверки страниц"""
        user_id = update.effective_user.id
        
        try:
            # Получаем отслеживаемые страницы пользователя
            pages = await self.db.get_user_pages(user_id)
            
            if not pages:
                await update.message.reply_text(
                    "📝 У вас пока нет отслеживаемых страниц.\n\n"
                    "Используйте /add для добавления страницы."
                )
                return
            
            await update.message.reply_text("🔍 Принудительная проверка страниц...")
            
            found_events = 0
            for page in pages:
                try:
                    site_name = page['site_name'] or self._extract_domain(page['url'])
                    await update.message.reply_text(f"🔍 Проверяю {site_name}...")
                    
                    new_events = await self.monitor.check_page_for_updates(page)
                    
                    if new_events:
                        found_events += len(new_events)
                        await self.send_notification(user_id, page, new_events)
                        
                        # Сохраняем новые события в базу
                        for event in new_events:
                            await self.db.add_event(
                                page_id=page['id'],
                                title=event['title'],
                                date=event.get('date'),
                                link=event.get('link'),
                                image_url=event.get('image_url'),
                                content_hash=event.get('content_hash')
                            )
                    
                except Exception as e:
                    logger.error(f"Ошибка проверки {page['url']}: {e}")
                    await update.message.reply_text(f"❌ Ошибка проверки {site_name}: {str(e)}")
            
            await update.message.reply_text(
                f"✅ Проверка завершена!\n\n"
                f"📊 Найдено новых событий: {found_events}\n"
                f"🔗 Проверено страниц: {len(pages)}\n\n"
                f"💡 Автоматическая проверка происходит каждые {CHECK_INTERVAL_MINUTES} минут."
            )
            
        except Exception as e:
            logger.error(f"Ошибка проверки: {e}")
            await update.message.reply_text(f"❌ Ошибка проверки: {str(e)}")
    
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений с URL"""
        text = update.message.text.strip()
        
        # Проверяем, является ли сообщение URL
        if self._is_valid_url(text):
            # Добавляем страницу
            user_id = update.effective_user.id
            site_name = self._extract_domain(text)
            
            try:
                # Проверяем, не добавлена ли уже эта страница
                pages = await self.db.get_user_pages(user_id)
                for page in pages:
                    if page['url'] == text:
                        await update.message.reply_text("⚠️ Эта страница уже отслеживается!")
                        return
                
                # Добавляем страницу
                await self.db.add_monitored_page(user_id, text, site_name)
                await update.message.reply_text(
                    f"✅ Страница добавлена для мониторинга!\n\n"
                    f"🔗 {site_name}\n"
                    f"📅 Бот будет проверять обновления каждые {CHECK_INTERVAL_MINUTES} минут."
                )
                
            except Exception as e:
                logger.error(f"Ошибка добавления страницы: {e}")
                await update.message.reply_text("❌ Ошибка добавления страницы.")
        else:
            await update.message.reply_text(
                "❓ Не понимаю команду. Отправьте ссылку на страницу для мониторинга или используйте /help для справки."
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith('remove_'):
            page_id = int(query.data.split('_')[1])
            user_id = update.effective_user.id
            
            try:
                success = await self.db.remove_page(page_id, user_id)
                if success:
                    await query.edit_message_text("✅ Страница удалена из мониторинга.")
                else:
                    await query.edit_message_text("❌ Ошибка удаления страницы.")
            except Exception as e:
                logger.error(f"Ошибка удаления страницы: {e}")
                await query.edit_message_text("❌ Ошибка удаления страницы.")
    
    async def send_notification(self, user_id: int, page_info: Dict, events: List[Dict]):
        """Отправка уведомления о новых событиях"""
        try:
            site_name = page_info['site_name'] or self._extract_domain(page_info['url'])
            
            for event in events:
                # Формируем сообщение
                message = f"🎵 Новое событие на {site_name}!\n\n"
                message += f"📝 {event['title']}\n"
                
                if event.get('date'):
                    message += f"📅 {event['date']}\n"
                
                if event.get('link'):
                    message += f"🔗 {event['link']}\n"
                
                # Отправляем изображение, если есть
                if event.get('image_url'):
                    try:
                        await self.application.bot.send_photo(
                            chat_id=user_id,
                            photo=event['image_url'],
                            caption=message
                        )
                        logger.info(f"Отправлено изображение: {event['image_url']}")
                    except TelegramError as e:
                        logger.error(f"Ошибка отправки изображения {event['image_url']}: {e}")
                        # Отправляем текстовое сообщение с информацией об изображении
                        message += f"\n🖼️ Изображение: {event['image_url']}"
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message
                        )
                else:
                    # Отправляем текстовое сообщение
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=message
                    )
                
                # Небольшая задержка между сообщениями
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
    
    async def run_monitoring(self):
        """Запуск мониторинга страниц"""
        logger.info("🔄 Запуск мониторинга страниц...")
        
        while True:
            try:
                pages = await self.db.get_all_monitored_pages()
                logger.info(f"📊 Проверяю {len(pages)} страниц...")
                
                for page in pages:
                    try:
                        logger.info(f"🔍 Проверяю страницу: {page['url']}")
                        new_events = await self.monitor.check_page_for_updates(page)
                        
                        if new_events:
                            logger.info(f"🎵 Найдено {len(new_events)} новых событий на {page['url']}")
                            await self.send_notification(page['user_id'], page, new_events)
                            
                            # Сохраняем новые события в базу
                            for event in new_events:
                                await self.db.add_event(
                                    page_id=page['id'],
                                    title=event['title'],
                                    date=event.get('date'),
                                    link=event.get('link'),
                                    image_url=event.get('image_url'),
                                    content_hash=event.get('content_hash')
                                )
                        else:
                            logger.info(f"✅ Новых событий нет на {page['url']}")
                    
                    except Exception as e:
                        logger.error(f"Ошибка мониторинга страницы {page['url']}: {e}")
                
                logger.info(f"⏰ Жду {CHECK_INTERVAL_MINUTES} минут до следующей проверки...")
                # Ждем перед следующей проверкой
                await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def start_bot(self):
        """Запуск бота"""
        # Инициализация базы данных
        await self.db.init_db()
        
        # Создание приложения
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("add", self.add_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("remove", self.remove_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        self.application.add_handler(CommandHandler("sites", self.sites_command))
        self.application.add_handler(CommandHandler("images", self.images_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("simulate", self.simulate_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url_message))
        
        # Запуск бота
        await self.application.initialize()
        await self.application.start()
        
        logger.info("Бот запущен!")
        
        # Запуск мониторинга в фоновом режиме
        asyncio.create_task(self.run_monitoring())
        
        # Ожидание завершения
        await self.application.updater.start_polling()
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения...")
        finally:
            await self.application.stop()
            await self.monitor.close_session()