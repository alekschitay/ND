import aiohttp
import asyncio
import hashlib
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import config
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class PageMonitor:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def _get_session(self):
        """Получение HTTP сессии"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self.session

    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_page(self, url: str) -> Optional[str]:
        """Загрузка страницы"""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                else:
                    logger.warning(f"HTTP {response.status} для {url}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None

    def calculate_content_hash(self, content: str) -> str:
        """Вычисление хеша содержимого страницы"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def extract_events_from_html(self, html: str, url: str) -> List[Dict]:
        """Извлечение событий из HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            events = []
            
            # Получаем паттерны для сайта
            patterns = self._get_site_patterns(url)
            
            # Ищем элементы событий
            event_elements = soup.select(patterns['event_selector'])
            
            for element in event_elements:
                event_data = self._extract_event_data(element, url, patterns)
                if event_data:
                    # Если нет заголовка, но есть изображение, используем изображение
                    if not event_data['title'] and event_data.get('image_url'):
                        event_data['title'] = "🎵 Новое событие"
                    events.append(event_data)
            
            # Если не нашли события по селекторам, ищем по ключевым словам
            if not events:
                events = self._search_by_keywords(soup, url)
            
            # Если все еще нет событий, ищем только изображения
            if not events:
                events = self._extract_image_only_events(soup, url, patterns)
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML: {e}")
            return []

    def _get_site_patterns(self, url: str) -> Dict:
        """Получение паттернов для конкретного сайта"""
        from site_configs import get_config_for_domain
        domain = urlparse(url).netloc.lower()
        
        # Получаем конфигурацию для домена
        site_config = get_config_for_domain(domain)
        
        # Возвращаем только селекторы
        return {
            'event_selector': site_config['event_selector'],
            'title_selector': site_config['title_selector'],
            'date_selector': site_config['date_selector'],
            'link_selector': site_config['link_selector'],
            'image_selector': site_config['image_selector']
        }

    def _extract_event_data(self, element, base_url: str, patterns: Dict) -> Optional[Dict]:
        """Извлечение данных события из элемента"""
        try:
            # Извлекаем заголовок
            title_element = element.select_one(patterns['title_selector'])
            title = title_element.get_text(strip=True) if title_element else ""
            
            # Если нет заголовка, пытаемся извлечь из alt или title изображения
            if not title:
                img_element = element.select_one(patterns['image_selector'])
                if img_element:
                    title = img_element.get('alt', '') or img_element.get('title', '')
            
            # Если все еще нет заголовка, извлекаем из текста элемента
            if not title:
                element_text = element.get_text(strip=True)
                if element_text and len(element_text) > 10:
                    title = element_text[:100]  # Первые 100 символов
            
            # Если заголовок все еще пустой, но есть изображение, создаем общий заголовок
            if not title:
                img_element = element.select_one(patterns['image_selector'])
                if img_element and img_element.get('src'):
                    title = "🎵 Новое событие"
                else:
                    return None  # Нет ни заголовка, ни изображения
            
            # Извлекаем дату
            date_element = element.select_one(patterns['date_selector'])
            date = date_element.get_text(strip=True) if date_element else ""
            
            # Извлекаем ссылку
            link_element = element.select_one(patterns['link_selector'])
            link = ""
            if link_element and link_element.get('href'):
                link = urljoin(base_url, link_element['href'])
            
            # Извлекаем изображение
            image_element = element.select_one(patterns['image_selector'])
            image_url = ""
            if image_element and image_element.get('src'):
                src = image_element.get('src')
                # Проверяем, что это не служебное изображение
                if self._is_event_image(image_element):
                    image_url = urljoin(base_url, src)
            
            # Создаем хеш для уникальности события
            content_hash = hashlib.md5(f"{title}{date}{link}{image_url}".encode()).hexdigest()
            
            return {
                'title': title,
                'date': date,
                'link': link,
                'image_url': image_url,
                'content_hash': content_hash
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных события: {e}")
            return None

    def _search_by_keywords(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Поиск событий по ключевым словам"""
        events = []
        
        # Ключевые слова для поиска событий
        keywords = [
            'концерт', 'concert', 'шоу', 'show', 'фестиваль', 'festival',
            'выступление', 'performance', 'гастроли', 'tour', 'афиша'
        ]
        
        # Ищем элементы с ключевыми словами
        for keyword in keywords:
            elements = soup.find_all(text=re.compile(keyword, re.IGNORECASE))
            
            for element in elements:
                parent = element.parent
                if parent and parent.name in ['div', 'article', 'section', 'li']:
                    event_data = self._extract_event_from_text(parent, url)
                    if event_data and event_data['title']:
                        events.append(event_data)
        
        return events

    def _extract_event_from_text(self, element, base_url: str) -> Optional[Dict]:
        """Извлечение события из текстового элемента"""
        try:
            text = element.get_text(strip=True)
            if len(text) < 10:  # Слишком короткий текст
                return None
            
            # Ищем ссылки в элементе
            link_element = element.find('a')
            link = ""
            if link_element and link_element.get('href'):
                link = urljoin(base_url, link_element['href'])
            
            # Ищем изображения
            image_element = element.find('img')
            image_url = ""
            if image_element and image_element.get('src'):
                image_url = urljoin(base_url, image_element['src'])
            
            # Извлекаем дату из текста
            date = self._extract_date_from_text(text)
            
            # Создаем заголовок (первые слова текста)
            title = text[:100] + "..." if len(text) > 100 else text
            
            content_hash = hashlib.md5(f"{title}{date}{link}".encode()).hexdigest()
            
            return {
                'title': title,
                'date': date,
                'link': link,
                'image_url': image_url,
                'content_hash': content_hash
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения события из текста: {e}")
            return None

    def _extract_date_from_text(self, text: str) -> str:
        """Извлечение даты из текста"""
        # Паттерны для поиска дат
        date_patterns = [
            r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
            r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
            r'\d{1,2}\s+\w+\s+\d{4}',    # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        
        return ""

    def _extract_image_only_events(self, soup: BeautifulSoup, base_url: str, patterns: Dict) -> List[Dict]:
        """Извлечение событий только по изображениям (для страниц с графическими афишами)"""
        events = []
        
        try:
            # Ищем все изображения на странице
            images = soup.find_all('img')
            
            for img in images:
                # Проверяем, что это не служебное изображение
                if self._is_event_image(img):
                    event_data = self._extract_event_from_image(img, base_url)
                    if event_data:
                        events.append(event_data)
            
            # Если не нашли по img, ищем по контейнерам с изображениями
            if not events:
                events = self._extract_events_from_image_containers(soup, base_url, patterns)
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка извлечения событий по изображениям: {e}")
            return []

    def _is_event_image(self, img_element) -> bool:
        """Проверка, является ли изображение афишей события"""
        try:
            # Проверяем атрибуты изображения
            src = img_element.get('src', '').lower()
            alt = img_element.get('alt', '').lower()
            title = img_element.get('title', '').lower()
            class_name = ' '.join(img_element.get('class', [])).lower()
            
            # Исключаем явно служебные изображения
            exclude_keywords = [
                'logo', 'icon', 'avatar', 'profile', 'banner', 'header', 'footer',
                'social', 'facebook', 'twitter', 'instagram', 'vk', 'youtube',
                'loading', 'spinner', 'placeholder', 'default', 'no-image',
                'svg', 'gif', 'favicon', 'apple-touch'
            ]
            
            # Проверяем, что это не служебное изображение
            for keyword in exclude_keywords:
                if keyword in src or keyword in alt or keyword in title or keyword in class_name:
                    return False
            
            # Проверяем размеры изображения (примерно)
            width = img_element.get('width', '')
            height = img_element.get('height', '')
            
            # Если есть размеры, проверяем что это не маленькая иконка
            if width and height:
                try:
                    w = int(width.replace('px', ''))
                    h = int(height.replace('px', ''))
                    if w < 50 or h < 50:  # Снизили порог до 50x50
                        return False
                except:
                    pass
            
            # Проверяем расширение файла
            if src.endswith(('.svg', '.gif', '.ico')):
                return False
            
            # Если изображение имеет разумные размеры и не исключено, считаем его событием
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки изображения: {e}")
            return False

    def _extract_event_from_image(self, img_element, base_url: str) -> Optional[Dict]:
        """Извлечение данных события из изображения"""
        try:
            src = img_element.get('src', '')
            if not src:
                return None
            
            # Получаем полный URL изображения
            image_url = urljoin(base_url, src)
            
            # Извлекаем заголовок из alt или title
            title = img_element.get('alt', '') or img_element.get('title', '')
            if not title:
                # Пытаемся извлечь из родительского элемента
                parent = img_element.parent
                if parent:
                    title = parent.get_text(strip=True)[:100]  # Первые 100 символов
            
            # Если заголовка нет, создаем общий
            if not title:
                title = "🎵 Новое событие"
            
            # Ищем ссылку на событие (в родительском элементе)
            link = ""
            parent = img_element.parent
            while parent and parent.name != 'body':
                if parent.name == 'a' and parent.get('href'):
                    link = urljoin(base_url, parent['href'])
                    break
                parent = parent.parent
            
            # Создаем хеш для уникальности
            content_hash = hashlib.md5(f"{image_url}{title}".encode()).hexdigest()
            
            return {
                'title': title,
                'date': "",  # Для графических афиш дата обычно в изображении
                'link': link,
                'image_url': image_url,
                'content_hash': content_hash
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения события из изображения: {e}")
            return None

    def _extract_events_from_image_containers(self, soup: BeautifulSoup, base_url: str, patterns: Dict) -> List[Dict]:
        """Извлечение событий из контейнеров с изображениями"""
        events = []
        
        try:
            # Ищем контейнеры, которые могут содержать афиши
            container_selectors = [
                '.poster', '.event', '.concert', '.show', '.afisha',
                '[class*="poster"]', '[class*="event"]', '[class*="concert"]',
                '.card', '.item', '.tile', '.block'
            ]
            
            for selector in container_selectors:
                containers = soup.select(selector)
                
                for container in containers:
                    # Ищем изображение в контейнере
                    img = container.find('img')
                    if img and self._is_event_image(img):
                        event_data = self._extract_event_from_image(img, base_url)
                        
                        # Пытаемся извлечь дополнительную информацию из контейнера
                        if event_data:
                            # Ищем ссылку в контейнере
                            link_elem = container.find('a')
                            if link_elem and link_elem.get('href'):
                                event_data['link'] = urljoin(base_url, link_elem['href'])
                            
                            # Ищем текст в контейнере для заголовка
                            container_text = container.get_text(strip=True)
                            if container_text and len(container_text) > len(event_data['title']):
                                event_data['title'] = container_text[:100]
                            
                            events.append(event_data)
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка извлечения событий из контейнеров: {e}")
            return []

    async def check_page_for_updates(self, page_info: Dict) -> List[Dict]:
        """Проверка страницы на обновления"""
        try:
            url = page_info['url']
            last_hash = page_info.get('last_hash')
            
            # Загружаем страницу
            content = await self.fetch_page(url)
            if not content:
                return []
            
            # Вычисляем хеш содержимого
            current_hash = self.calculate_content_hash(content)
            
            # Если хеш не изменился, обновлений нет
            if last_hash and last_hash == current_hash:
                return []
            
            # Извлекаем события
            events = self.extract_events_from_html(content, url)
            
            # Если это первая проверка, не отправляем все события
            if not last_hash:
                # Обновляем хеш, но не отправляем события
                from database import Database
                db = Database()
                await db.update_page_hash(page_info['id'], current_hash)
                return []
            
            # Фильтруем новые события
            new_events = []
            existing_events = await self._get_existing_events(page_info['id'])
            existing_hashes = {event['content_hash'] for event in existing_events}
            
            for event in events:
                if event['content_hash'] not in existing_hashes:
                    new_events.append(event)
            
            # Обновляем хеш страницы
            from database import Database
            db = Database()
            await db.update_page_hash(page_info['id'], current_hash)
            
            return new_events[:config.MAX_EVENTS_PER_CHECK]
            
        except Exception as e:
            logger.error(f"Ошибка проверки страницы {page_info['url']}: {e}")
            return []

    async def _get_existing_events(self, page_id: int) -> List[Dict]:
        """Получение существующих событий для страницы"""
        try:
            from database import Database
            db = Database()
            return await db.get_recent_events(page_id, limit=50)
        except Exception as e:
            logger.error(f"Ошибка получения существующих событий: {e}")
            return []

    async def test_page_parsing(self, url: str) -> Dict:
        """Тестирование парсинга страницы (для отладки)"""
        try:
            content = await self.fetch_page(url)
            if not content:
                return {'error': 'Не удалось загрузить страницу'}
            
            events = self.extract_events_from_html(content, url)
            
            return {
                'url': url,
                'events_found': len(events),
                'events': events[:5],  # Показываем только первые 5
                'content_length': len(content)
            }
            
        except Exception as e:
            return {'error': str(e)}