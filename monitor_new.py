"""
Модуль для мониторинга веб-страниц и извлечения событий
"""

import asyncio
import aiohttp
import hashlib
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config_new import (
    REQUEST_TIMEOUT, REQUEST_DELAY, MIN_IMAGE_SIZE, MAX_IMAGE_SIZE,
    EVENT_KEYWORDS, EXCLUDE_IMAGE_KEYWORDS, SUPPORTED_IMAGE_FORMATS
)

logger = logging.getLogger(__name__)

class PageMonitor:
    def __init__(self):
        self.session = None
    
    async def _get_session(self):
        """Получение HTTP сессии"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Загрузка страницы с улучшенными заголовками"""
        try:
            session = await self._get_session()
            
            # Улучшенные заголовки для обхода защиты
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                elif response.status == 202:
                    # Для статуса 202 ждем и повторяем запрос
                    logger.info(f"HTTP 202 для {url}, жду и повторяю...")
                    await asyncio.sleep(2)
                    async with session.get(url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            content = await retry_response.text()
                            return content
                        else:
                            logger.warning(f"Повторный HTTP {retry_response.status} для {url}")
                            return None
                else:
                    logger.warning(f"HTTP {response.status} для {url}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None
    
    def calculate_content_hash(self, content: str) -> str:
        """Вычисление хеша содержимого страницы"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_site_config(self, url: str) -> Dict:
        """Получение конфигурации для сайта"""
        domain = urlparse(url).netloc.lower()
        
        # Конфигурации для популярных сайтов
        site_configs = {
            'memobar.ru': {
                'event_selector': '#rec355567016 img, .t-popup__container img',
                'title_selector': 'img[alt], img[title]',
                'image_selector': 'img',
                'is_poster_site': True
            },
            'viagogo.com': {
                'event_selector': '.event-item, .concert-item, [data-testid="event-card"], .event-card, .event',
                'title_selector': '.event-title, .concert-title, h3, h4, [data-testid="event-title"], .title',
                'date_selector': '.event-date, .concert-date, .date, [data-testid="event-date"], .datetime',
                'link_selector': 'a',
                'image_selector': 'img'
            },
            'kremlinpalace.org': {
                'event_selector': '.event-item, .concert-item, .performance-item',
                'title_selector': '.event-title, .concert-title, h3, h4',
                'date_selector': '.event-date, .concert-date, .date',
                'link_selector': 'a',
                'image_selector': 'img'
            }
        }
        
        # Проверяем точное совпадение домена
        for site_domain, config in site_configs.items():
            if site_domain in domain:
                return config
        
        # Проверяем ключевые слова для определения типа сайта
        if any(keyword in domain for keyword in ['poster', 'afisha', 'афиша', 'posters']):
            return {
                'event_selector': 'img',
                'title_selector': 'img[alt], img[title]',
                'image_selector': 'img',
                'is_poster_site': True
            }
        
        # Стандартная конфигурация
        return {
            'event_selector': '.event, .concert, .performance, .show, [class*="event"], [class*="concert"]',
            'title_selector': 'h1, h2, h3, h4, .title, .name, [class*="title"], [class*="name"]',
            'date_selector': '.date, .time, .datetime, [class*="date"], [class*="time"]',
            'link_selector': 'a',
            'image_selector': 'img'
        }
    
    def _is_event_image(self, img_url: str, img_element) -> bool:
        """Проверка, является ли изображение событием"""
        if not img_url:
            return False
        
        # Проверяем размер изображения
        try:
            width = img_element.get('width')
            height = img_element.get('height')
            if width and height:
                w, h = int(width), int(height)
                if w < MIN_IMAGE_SIZE or h < MIN_IMAGE_SIZE:
                    return False
                if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
                    return False
        except (ValueError, TypeError):
            pass
        
        # Проверяем исключаемые ключевые слова
        img_url_lower = img_url.lower()
        for keyword in EXCLUDE_IMAGE_KEYWORDS:
            if keyword in img_url_lower:
                return False
        
        # Проверяем формат изображения
        if not any(img_url_lower.endswith(fmt) for fmt in SUPPORTED_IMAGE_FORMATS):
            return False
        
        return True
    
    def _get_fullsize_image_url(self, img_url: str) -> str:
        """Получение URL изображения в полном размере"""
        if not img_url:
            return img_url
        
        # Убираем параметры изменения размера для популярных CDN
        img_url = img_url.replace('/resize/', '/')
        img_url = img_url.replace('/w_', '/')
        img_url = img_url.replace('/h_', '/')
        img_url = img_url.replace('/c_', '/')
        
        # Убираем параметры качества
        if '?' in img_url:
            base_url = img_url.split('?')[0]
            img_url = base_url
        
        return img_url
    
    def extract_events_from_html(self, html_content: str, url: str) -> List[Dict]:
        """Извлечение событий из HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            config = self._get_site_config(url)
            
            events = []
            
            # Если это сайт с постером, используем специальную логику
            if config.get('is_poster_site'):
                events = self._extract_poster_events(soup, url, config)
            else:
                events = self._extract_text_events(soup, url, config)
            
            # Если события не найдены, пробуем общий поиск
            if not events:
                events = self._extract_general_events(soup, url)
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка извлечения событий: {e}")
            return []
    
    def _extract_poster_events(self, soup: BeautifulSoup, url: str, config: Dict) -> List[Dict]:
        """Извлечение событий с графическими постерами"""
        events = []
        
        try:
            # Ищем изображения по селектору
            images = soup.select(config['image_selector'])
            
            for img in images:
                img_url = img.get('src') or img.get('data-src')
                if not img_url:
                    continue
                
                # Преобразуем относительный URL в абсолютный
                img_url = urljoin(url, img_url)
                
                # Проверяем, подходит ли изображение
                if not self._is_event_image(img_url, img):
                    continue
                
                # Получаем полный размер изображения
                fullsize_url = self._get_fullsize_image_url(img_url)
                
                # Извлекаем название
                title = (img.get('alt') or 
                        img.get('title') or 
                        img.get('data-title') or
                        '🎵 Новое событие')
                
                # Ищем ссылку на событие
                link = url
                parent_link = img.find_parent('a')
                if parent_link and parent_link.get('href'):
                    link = urljoin(url, parent_link.get('href'))
                
                event = {
                    'title': title.strip(),
                    'date': '',  # Дата в изображении
                    'link': link,
                    'image_url': fullsize_url,
                    'content_hash': hashlib.md5(f"{title}{fullsize_url}".encode()).hexdigest()
                }
                
                events.append(event)
                
        except Exception as e:
            logger.error(f"Ошибка извлечения постеров: {e}")
        
        return events
    
    def _extract_text_events(self, soup: BeautifulSoup, url: str, config: Dict) -> List[Dict]:
        """Извлечение текстовых событий"""
        events = []
        
        try:
            # Ищем элементы событий
            event_elements = soup.select(config['event_selector'])
            
            for element in event_elements:
                # Извлекаем название
                title_element = element.select_one(config['title_selector'])
                title = title_element.get_text(strip=True) if title_element else ''
                
                if not title:
                    continue
                
                # Проверяем, содержит ли название ключевые слова событий
                if not any(keyword.lower() in title.lower() for keyword in EVENT_KEYWORDS):
                    continue
                
                # Извлекаем дату
                date_element = element.select_one(config['date_selector'])
                date = date_element.get_text(strip=True) if date_element else ''
                
                # Извлекаем ссылку
                link_element = element.select_one(config['link_selector'])
                link = urljoin(url, link_element.get('href')) if link_element and link_element.get('href') else url
                
                # Извлекаем изображение
                img_element = element.select_one(config['image_selector'])
                image_url = ''
                if img_element:
                    img_url = img_element.get('src') or img_element.get('data-src')
                    if img_url:
                        image_url = urljoin(url, img_url)
                        image_url = self._get_fullsize_image_url(image_url)
                
                event = {
                    'title': title,
                    'date': date,
                    'link': link,
                    'image_url': image_url,
                    'content_hash': hashlib.md5(f"{title}{date}{link}".encode()).hexdigest()
                }
                
                events.append(event)
                
        except Exception as e:
            logger.error(f"Ошибка извлечения текстовых событий: {e}")
        
        return events
    
    def _extract_general_events(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Общий поиск событий"""
        events = []
        
        try:
            # Ищем все ссылки с ключевыми словами
            links = soup.find_all('a', href=True)
            
            for link in links:
                text = link.get_text(strip=True)
                if not text:
                    continue
                
                # Проверяем ключевые слова
                if any(keyword.lower() in text.lower() for keyword in EVENT_KEYWORDS):
                    # Ищем изображение рядом
                    img = link.find('img') or link.find_next('img')
                    image_url = ''
                    if img:
                        img_url = img.get('src') or img.get('data-src')
                        if img_url:
                            image_url = urljoin(url, img_url)
                            image_url = self._get_fullsize_image_url(image_url)
                    
                    event = {
                        'title': text,
                        'date': '',
                        'link': urljoin(url, link.get('href')),
                        'image_url': image_url,
                        'content_hash': hashlib.md5(f"{text}{link.get('href')}".encode()).hexdigest()
                    }
                    
                    events.append(event)
                    
        except Exception as e:
            logger.error(f"Ошибка общего поиска событий: {e}")
        
        return events
    
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
            
            # Извлекаем события
            events = self.extract_events_from_html(content, url)
            
            # Обновляем время последней проверки ВСЕГДА
            from database_new import Database
            db = Database()
            await db.update_page_hash(page_info['id'], current_hash)
            
            # Если хеш не изменился, обновлений нет
            if last_hash and last_hash == current_hash:
                return []
            
            # Если это первая проверка, не отправляем все события
            if not last_hash:
                return []
            
            # Фильтруем новые события
            new_events = []
            existing_events = await self._get_existing_events(page_info['id'])
            existing_hashes = {event['content_hash'] for event in existing_events}
            
            for event in events:
                if event['content_hash'] not in existing_hashes:
                    new_events.append(event)
            
            return new_events[:10]  # Ограничиваем количество
            
        except Exception as e:
            logger.error(f"Ошибка проверки страницы {page_info['url']}: {e}")
            return []
    
    async def _get_existing_events(self, page_id: int) -> List[Dict]:
        """Получение существующих событий для страницы"""
        try:
            from database_new import Database
            db = Database()
            return await db.get_page_events(page_id)
        except Exception as e:
            logger.error(f"Ошибка получения существующих событий: {e}")
            return []
    
    async def test_page_parsing(self, url: str) -> Dict:
        """Тестирование парсинга страницы"""
        try:
            content = await self.fetch_page(url)
            if not content:
                return {'error': 'Не удалось загрузить страницу'}
            
            events = self.extract_events_from_html(content, url)
            
            return {
                'url': url,
                'content_length': len(content),
                'events_found': len(events),
                'events': events[:5]  # Показываем только первые 5
            }
            
        except Exception as e:
            return {'error': str(e)}