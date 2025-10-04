import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import config
from database import Database
from monitor import PageMonitor
import re

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

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        await self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = f"""
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
/help - Помощь

🔗 Чтобы добавить страницу для мониторинга, используйте команду /add или просто отправьте ссылку на страницу.

🖼️ Для страниц с графическими афишами используйте команду /images для тестирования.
📊 Используйте /status для проверки работы мониторинга.
        """
        
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🎵 Concert Monitor Bot - Помощь

📋 Команды:
/start - Начать работу с ботом
/add - Добавить страницу для мониторинга
/list - Показать все отслеживаемые страницы
/remove - Удалить страницу из мониторинга
/test - Тестировать парсинг страницы
/images - Тестировать извлечение изображений-афиш
/sites - Показать поддерживаемые сайты
/help - Показать эту справку

🔗 Как добавить страницу:
1. Используйте команду /add
2. Или просто отправьте ссылку на страницу

📊 Что отслеживается:
• Новые события (концерты, шоу)
• Даты событий
• Ссылки на события
• Графические афиши

⚡ Уведомления приходят только при появлении новых событий на отслеживаемых страницах.

🔍 Команда /test позволяет проверить, как бот парсит конкретную страницу.
🖼️ Команда /images специально для страниц с графическими афишами.
🌐 Команда /sites показывает список оптимизированных сайтов.
        """
        await update.message.reply_text(help_text)

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /add"""
        await update.message.reply_text(
            "🔗 Отправьте ссылку на страницу, которую хотите отслеживать:\n\n"
            "Например: https://example.com/events"
        )

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /list"""
        user_id = update.effective_user.id
        pages = await self.db.get_user_pages(user_id)
        
        if not pages:
            await update.message.reply_text("📝 У вас пока нет отслеживаемых страниц.\n\nИспользуйте /add для добавления.")
            return
        
        text = "📋 Ваши отслеживаемые страницы:\n\n"
        keyboard = []
        
        for page in pages:
            site_name = page['site_name'] or self._extract_domain(page['url'])
            text += f"🔗 {site_name}\n"
            text += f"   URL: {page['url']}\n"
            text += f"   Добавлена: {page['created_at'][:10]}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"❌ Удалить {site_name}",
                callback_data=f"remove_{page['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)

    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /remove"""
        await self.list_command(update)

    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test для тестирования парсинга"""
        if not context.args:
            await update.message.reply_text(
                "🔍 Использование: /test <URL>\n\n"
                "Пример: /test https://example.com/events"
            )
            return
        
        url = context.args[0]
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
                for i, event in enumerate(result['events'][:3], 1):
                    text += f"{i}. {event['title']}\n"
                    if event['date']:
                        text += f"   📅 {event['date']}\n"
                    if event['link']:
                        text += f"   🔗 {event['link']}\n"
                    if event.get('image_url'):
                        text += f"   🖼️ Изображение: {event['image_url']}\n"
                    text += "\n"
                
                # Показываем статистику по изображениям
                images_count = sum(1 for event in result['events'] if event.get('image_url'))
                text += f"🖼️ Событий с изображениями: {images_count} из {len(result['events'])}\n"
                
                # Отправляем первое изображение как пример
                first_image_event = None
                for event in result['events']:
                    if event.get('image_url'):
                        first_image_event = event
                        break
                
                if first_image_event:
                    text += f"\n📸 Отправляю пример изображения..."
                    await update.message.reply_text(text)
                    
                    try:
                        logger.info(f"Тестирую отправку изображения: {first_image_event['image_url']}")
                        
                        # Отправляем изображение
                        message = await self.application.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=first_image_event['image_url'],
                            caption=f"Пример: {first_image_event['title']}"
                        )
                        
                        logger.info(f"Тестовое изображение успешно отправлено. Message ID: {message.message_id}")
                        
                        # Отправляем подтверждение
                        await self.application.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"✅ Изображение отправлено!\n\n🔗 URL: {first_image_event['image_url']}"
                        )
                        
                    except Exception as e:
                        logger.error(f"Ошибка тестовой отправки изображения: {e}")
                        logger.error(f"Тип ошибки: {type(e).__name__}")
                        await self.application.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"⚠️ Не удалось отправить изображение: {str(e)}\n\n🔗 URL: {first_image_event['image_url']}"
                        )
                else:
                    await update.message.reply_text(text)
            else:
                text += "⚠️ События не найдены. Возможно, нужно настроить селекторы для этого сайта."
                await update.message.reply_text(text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка тестирования: {str(e)}")

    async def sites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /sites для просмотра поддерживаемых сайтов"""
        try:
            from site_configs import list_supported_sites
            
            sites = list_supported_sites()
            
            text = "🌐 Поддерживаемые сайты:\n\n"
            
            for site in sites:
                text += f"🔗 {site['name']} ({site['domain']})\n"
                text += f"   {site['description']}\n\n"
            
            text += "💡 Бот также может работать с другими сайтами, используя общие селекторы."
            
            await update.message.reply_text(text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения списка сайтов: {str(e)}")

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
            
            text += f"⏰ Интервал проверки: {config.CHECK_INTERVAL_MINUTES} минут\n"
            text += f"🤖 Бот работает и мониторит ваши страницы!\n\n"
            text += "💡 Когда на сайтах появятся новые события, вы получите уведомления."
            
            await update.message.reply_text(text)
            
        except Exception as e:
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
                f"💡 Автоматическая проверка происходит каждые {config.CHECK_INTERVAL_MINUTES} минут."
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка проверки: {str(e)}")

    async def images_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /images для тестирования извлечения изображений"""
        if not context.args:
            await update.message.reply_text(
                "🖼️ Использование: /images <URL>\n\n"
                "Пример: /images https://example.com/posters\n\n"
                "Эта команда специально для страниц с графическими афишами."
            )
            return
        
        url = context.args[0]
        if not self._is_valid_url(url):
            await update.message.reply_text("❌ Пожалуйста, укажите корректную ссылку.")
            return
        
        await update.message.reply_text("🖼️ Тестирую извлечение изображений...")
        
        try:
            # Загружаем страницу
            content = await self.monitor.fetch_page(url)
            if not content:
                await update.message.reply_text("❌ Не удалось загрузить страницу")
                return
            
            # Извлекаем только изображения
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            soup = BeautifulSoup(content, 'html.parser')
            
            images = soup.find_all('img')
            found_images = []
            
            for img in images:
                if self.monitor._is_event_image(img):
                    src = img.get('src', '')
                    if src:
                        image_url = urljoin(url, src)
                        alt = img.get('alt', '') or img.get('title', '') or 'Без описания'
                        found_images.append({
                            'url': image_url,
                            'alt': alt,
                            'width': img.get('width', ''),
                            'height': img.get('height', '')
                        })
            
            if found_images:
                text = f"🖼️ Найдено {len(found_images)} изображений-афиш:\n\n"
                
                for i, img in enumerate(found_images[:5], 1):  # Показываем первые 5
                    text += f"{i}. {img['alt']}\n"
                    text += f"   📏 {img['width']}x{img['height']}\n"
                    text += f"   🔗 {img['url']}\n\n"
                
                if len(found_images) > 5:
                    text += f"... и еще {len(found_images) - 5} изображений"
                
                await update.message.reply_text(text)
                
                # Отправляем первое изображение как пример
                if found_images[0]['url']:
                    try:
                        await self.application.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=found_images[0]['url'],
                            caption=f"Пример афиши: {found_images[0]['alt']}"
                        )
                    except Exception as e:
                        await update.message.reply_text(f"⚠️ Не удалось отправить изображение: {str(e)}")
            else:
                await update.message.reply_text(
                    "❌ Изображения-афиши не найдены.\n\n"
                    "Возможные причины:\n"
                    "• Изображения слишком маленькие\n"
                    "• Изображения помечены как служебные\n"
                    "• Нужны специальные селекторы для этого сайта"
                )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка тестирования: {str(e)}")

    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик сообщений с URL"""
        text = update.message.text.strip()
        
        # Проверяем, является ли сообщение URL
        if not self._is_valid_url(text):
            await update.message.reply_text(
                "❌ Пожалуйста, отправьте корректную ссылку на страницу.\n\n"
                "Пример: https://example.com/events"
            )
            return
        
        user_id = update.effective_user.id
        
        # Проверяем, не отслеживается ли уже эта страница
        existing_pages = await self.db.get_user_pages(user_id)
        for page in existing_pages:
            if page['url'] == text:
                await update.message.reply_text("⚠️ Эта страница уже отслеживается!")
                return
        
        # Добавляем страницу
        site_name = self._extract_domain(text)
        page_id = await self.db.add_monitored_page(user_id, text, site_name)
        
        await update.message.reply_text(
            f"✅ Страница добавлена для мониторинга!\n\n"
            f"🔗 {site_name}\n"
            f"📊 Бот будет проверять обновления каждые {config.CHECK_INTERVAL_MINUTES} минут.\n\n"
            f"Используйте /list для просмотра всех отслеживаемых страниц."
        )

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith('remove_'):
            page_id = int(query.data.split('_')[1])
            user_id = update.effective_user.id
            
            # Получаем информацию о странице перед удалением
            pages = await self.db.get_user_pages(user_id)
            page_to_remove = None
            for page in pages:
                if page['id'] == page_id:
                    page_to_remove = page
                    break
            
            if page_to_remove:
                await self.db.delete_page(page_id, user_id)
                site_name = page_to_remove['site_name'] or self._extract_domain(page_to_remove['url'])
                await query.edit_message_text(f"✅ Страница {site_name} удалена из мониторинга.")
            else:
                await query.edit_message_text("❌ Страница не найдена.")

    def _is_valid_url(self, text: str) -> bool:
        """Проверка валидности URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(text) is not None

    def _extract_domain(self, url: str) -> str:
        """Извлечение домена из URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url

    async def send_notification(self, user_id: int, page_info: dict, events: list):
        """Отправка уведомления о новых событиях"""
        site_name = page_info['site_name'] or self._extract_domain(page_info['url'])
        
        if not events:
            return
        
        try:
            for event in events:
                # Формируем текст сообщения
                text = f"🎵 Новое событие на {site_name}!\n\n"
                text += f"🎤 {event['title']}\n"
                if event['date']:
                    text += f"📅 {event['date']}\n"
                if event['link']:
                    text += f"🔗 {event['link']}\n"
                
                # Если есть изображение, отправляем его с текстом
                if event.get('image_url'):
                    try:
                        # Проверяем, что URL изображения корректный
                        image_url = event['image_url']
                        if not image_url.startswith(('http://', 'https://')):
                            raise ValueError("Некорректный URL изображения")
                        
                        # Логируем попытку отправки
                        logger.info(f"Отправляю изображение: {image_url}")
                        
                        await self.application.bot.send_photo(
                            chat_id=user_id,
                            photo=image_url,
                            caption=text,
                            parse_mode=ParseMode.HTML
                        )
                        
                        logger.info(f"Изображение успешно отправлено: {image_url}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка отправки изображения {event['image_url']}: {e}")
                        logger.error(f"Тип ошибки: {type(e).__name__}")
                        
                        # Если изображение не отправилось, отправляем только текст
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=text + f"\n\n🖼️ Изображение: {event['image_url']}\n❌ Не удалось отправить изображение: {str(e)}",
                            parse_mode=ParseMode.HTML
                        )
                else:
                    # Если нет изображения, отправляем только текст
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode=ParseMode.HTML
                    )
                
                # Небольшая пауза между сообщениями
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
                
                logger.info(f"⏰ Жду {config.CHECK_INTERVAL_MINUTES} минут до следующей проверки...")
                # Ждем перед следующей проверкой
                await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке

    async def start_bot(self):
        """Запуск бота"""
        # Инициализация базы данных
        await self.db.init_db()
        
        # Создание приложения
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Добавление обработчиков
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
            logger.info("Остановка бота...")
        finally:
            await self.application.stop()

if __name__ == '__main__':
    bot = ConcertMonitorBot()
    asyncio.run(bot.start_bot())