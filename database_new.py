"""
Модуль для работы с базой данных SQLite
"""

import aiosqlite
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config_new import DATABASE_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица отслеживаемых страниц
            await db.execute('''
                CREATE TABLE IF NOT EXISTS monitored_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    site_name TEXT,
                    last_hash TEXT,
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, url)
                )
            ''')
            
            # Таблица событий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    date TEXT,
                    link TEXT,
                    image_url TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES monitored_pages (id)
                )
            ''')
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def add_user(self, telegram_id: int, username: str = None, 
                      first_name: str = None, last_name: str = None) -> int:
        """Добавление пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                # Пользователь уже существует
                cursor = await db.execute('''
                    SELECT id FROM users WHERE telegram_id = ?
                ''', (telegram_id,))
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получение пользователя по Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM users WHERE telegram_id = ?
            ''', (telegram_id,))
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'created_at': row[5]
                }
            return None
    
    async def add_monitored_page(self, user_id: int, url: str, site_name: str = None) -> int:
        """Добавление отслеживаемой страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO monitored_pages (user_id, url, site_name)
                VALUES (?, ?, ?)
            ''', (user_id, url, site_name))
            await db.commit()
            return cursor.lastrowid
    
    async def get_user_pages(self, user_id: int) -> List[Dict]:
        """Получение страниц пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM monitored_pages WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'url': row[2],
                    'site_name': row[3],
                    'last_hash': row[4],
                    'last_check': row[5],
                    'created_at': row[6]
                }
                for row in rows
            ]
    
    async def get_all_monitored_pages(self) -> List[Dict]:
        """Получение всех отслеживаемых страниц"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM monitored_pages ORDER BY last_check ASC
            ''')
            rows = await cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'url': row[2],
                    'site_name': row[3],
                    'last_hash': row[4],
                    'last_check': row[5],
                    'created_at': row[6]
                }
                for row in rows
            ]
    
    async def update_page_hash(self, page_id: int, content_hash: str):
        """Обновление хеша страницы и времени последней проверки"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE monitored_pages 
                SET last_hash = ?, last_check = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (content_hash, page_id))
            await db.commit()
    
    async def remove_page(self, page_id: int, user_id: int) -> bool:
        """Удаление страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                DELETE FROM monitored_pages 
                WHERE id = ? AND user_id = ?
            ''', (page_id, user_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def add_event(self, page_id: int, title: str, date: str = None, 
                       link: str = None, image_url: str = None, content_hash: str = None):
        """Добавление события"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO events (page_id, title, date, link, image_url, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (page_id, title, date, link, image_url, content_hash))
            await db.commit()
    
    async def get_page_events(self, page_id: int) -> List[Dict]:
        """Получение событий страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM events WHERE page_id = ?
                ORDER BY created_at DESC
            ''', (page_id,))
            rows = await cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'page_id': row[1],
                    'title': row[2],
                    'date': row[3],
                    'link': row[4],
                    'image_url': row[5],
                    'content_hash': row[6],
                    'created_at': row[7]
                }
                for row in rows
            ]