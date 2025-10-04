import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Database
DATABASE_PATH = 'concert_monitor.db'

# Monitoring settings
CHECK_INTERVAL_MINUTES = 5  # Проверка каждые 5 минут
MAX_EVENTS_PER_CHECK = 10   # Максимум событий за одну проверку

# Supported sites patterns
SITE_PATTERNS = {
    'default': {
        'event_selector': '.event, .concert, .show, [class*="event"], [class*="concert"]',
        'title_selector': 'h1, h2, h3, .title, .name, .event-title',
        'date_selector': '.date, .time, .event-date, [class*="date"]',
        'link_selector': 'a',
        'image_selector': 'img'
    }
}

# User settings
DEFAULT_USER_SETTINGS = {
    'notifications_enabled': True,
    'check_interval': CHECK_INTERVAL_MINUTES
}