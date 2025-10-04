import aiosqlite
import json
from datetime import datetime
from typing import List, Dict, Optional
import config

class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    settings TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица отслеживаемых страниц
            await db.execute('''
                CREATE TABLE IF NOT EXISTS monitored_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT NOT NULL,
                    site_name TEXT,
                    last_check TIMESTAMP,
                    last_hash TEXT,
                    settings TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица событий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id INTEGER,
                    title TEXT NOT NULL,
                    date TEXT,
                    link TEXT,
                    image_url TEXT,
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES monitored_pages (id)
                )
            ''')
            
            await db.commit()

    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            await db.commit()

    async def add_monitored_page(self, user_id: int, url: str, site_name: str = None, settings: Dict = None):
        """Добавить отслеживаемую страницу"""
        if settings is None:
            settings = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO monitored_pages (user_id, url, site_name, settings)
                VALUES (?, ?, ?, ?)
            ''', (user_id, url, site_name, json.dumps(settings)))
            await db.commit()
            return cursor.lastrowid

    async def get_user_pages(self, user_id: int) -> List[Dict]:
        """Получить все отслеживаемые страницы пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM monitored_pages WHERE user_id = ?
            ''', (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_monitored_pages(self) -> List[Dict]:
        """Получить все отслеживаемые страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT mp.*, u.username, u.first_name 
                FROM monitored_pages mp
                JOIN users u ON mp.user_id = u.user_id
            ''')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_page_hash(self, page_id: int, content_hash: str):
        """Обновить хеш содержимого страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE monitored_pages 
                SET last_hash = ?, last_check = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (content_hash, page_id))
            await db.commit()

    async def add_event(self, page_id: int, title: str, date: str = None, link: str = None, image_url: str = None, content_hash: str = None):
        """Добавить событие"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO events (page_id, title, date, link, image_url, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (page_id, title, date, link, image_url, content_hash))
            await db.commit()

    async def get_recent_events(self, page_id: int, limit: int = 10) -> List[Dict]:
        """Получить последние события для страницы"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM events 
                WHERE page_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (page_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_page(self, page_id: int, user_id: int):
        """Удалить отслеживаемую страницу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM monitored_pages 
                WHERE id = ? AND user_id = ?
            ''', (page_id, user_id))
            await db.commit()

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получить пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM users WHERE user_id = ?
            ''', (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None