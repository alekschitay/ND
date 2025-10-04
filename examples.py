#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Примеры использования телеграм-бота для мониторинга концертов
"""

# Примеры команд для бота:

EXAMPLES = {
    "start": "/start",
    "help": "/help", 
    "add_url": "/add https://example-concert-hall.com/events",
    "list_urls": "/list",
    "remove_url": "/remove 1",
    "status": "/status"
}

# Примеры ссылок для мониторинга (замените на реальные):

SAMPLE_URLS = [
    "https://example-concert-hall.com/events",
    "https://music-venue.ru/concerts", 
    "https://theater.com/afisha",
    "https://club-city.net/shows",
    "https://concert-palace.org/upcoming",
    "https://music-club.com/events",
    "https://arena-stadium.ru/concerts",
    "https://cultural-center.net/performances"
]

# Примеры сообщений бота:

BOT_RESPONSES = {
    "welcome": """
🎵 Добро пожаловать в бот мониторинга концертных площадок!

Этот бот поможет вам отслеживать новые события на сайтах концертных площадок.

📋 Доступные команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/help - показать справку

Просто отправьте ссылку на страницу с событиями, и я начну её отслеживать!
    """,
    
    "notification_example": """
🎵 Новые события на сайте!
🔗 https://example-concert-hall.com/events

📅 Концерт группы "Рок-звезды"
📆 15.12.2024 20:00
📍 Концертный зал "Мегаполис"
💰 от 1500 руб
🔗 https://example-concert-hall.com/event/123

📅 Джазовый вечер с оркестром
📆 18.12.2024 19:30
📍 Джаз-клуб "Блюз"
💰 от 2000 руб
🔗 https://example-concert-hall.com/event/124
    """,
    
    "help_text": """
🔍 Как использовать бота:

1. Отправьте ссылку на страницу с событиями концертной площадки
2. Бот начнет мониторить эту страницу каждые 10 минут
3. При появлении новых событий вы получите уведомление

📝 Формат уведомлений:
• Название события
• Дата проведения
• Ссылка на событие
• Афиша (если доступна)

⚙️ Команды:
/add <ссылка> - добавить ссылку для мониторинга
/list - показать все отслеживаемые ссылки
/remove <номер> - удалить ссылку из мониторинга
/status - показать статус мониторинга

💡 Совет: Добавляйте ссылки на конкретные разделы сайтов (например, /events, /concerts, /afisha)
    """
}

# Примеры HTML структуры для парсинга:

HTML_EXAMPLES = {
    "simple_event": """
    <div class="event">
        <h3 class="title">Концерт группы "Рок-звезды"</h3>
        <div class="date">15.12.2024 20:00</div>
        <div class="venue">Концертный зал "Мегаполис"</div>
        <div class="price">от 1500 руб</div>
        <a href="/event/123">Подробнее</a>
        <img src="/images/poster123.jpg" alt="Афиша">
    </div>
    """,
    
    "complex_event": """
    <article class="concert-card">
        <div class="event-image">
            <img src="/posters/jazz-night.jpg" alt="Джазовый вечер">
        </div>
        <div class="event-info">
            <h2 class="event-title">Джазовый вечер с оркестром</h2>
            <div class="event-details">
                <span class="datetime">18.12.2024 19:30</span>
                <span class="location">Джаз-клуб "Блюз"</span>
                <span class="ticket-price">от 2000 руб</span>
            </div>
            <a href="/concerts/jazz-night" class="buy-ticket">Купить билет</a>
        </div>
    </article>
    """,
    
    "list_events": """
    <div class="events-list">
        <div class="event-item">
            <h3>Концерт классической музыки</h3>
            <p class="date">20.12.2024</p>
            <p class="venue">Филармония</p>
            <a href="/event/classical">Подробнее</a>
        </div>
        <div class="event-item">
            <h3>Рок-фестиваль</h3>
            <p class="date">25.12.2024</p>
            <p class="venue">Стадион "Арена"</p>
            <a href="/event/rock-fest">Подробнее</a>
        </div>
    </div>
    """
}

# Примеры селекторов для разных сайтов:

SELECTOR_EXAMPLES = {
    "common_selectors": [
        ".event", ".concert", ".show", ".performance",
        "[class*='event']", "[class*='concert']", "[class*='show']",
        ".card", ".item", ".poster", ".ticket"
    ],
    
    "title_selectors": [
        "h1", "h2", "h3", "h4",
        ".title", ".name", ".event-title", ".concert-title",
        "[class*='title']", "[class*='name']"
    ],
    
    "date_selectors": [
        ".date", ".time", ".datetime",
        "[class*='date']", "[class*='time']", "[class*='datetime']"
    ],
    
    "venue_selectors": [
        ".venue", ".place", ".location", ".address",
        "[class*='venue']", "[class*='place']", "[class*='location']"
    ],
    
    "price_selectors": [
        ".price", ".cost", ".ticket", ".ticket-price",
        "[class*='price']", "[class*='cost']", "[class*='ticket']"
    ]
}

def print_examples():
    """Вывод примеров использования"""
    print("🎵 Примеры использования телеграм-бота")
    print("=" * 50)
    
    print("\n📋 Команды бота:")
    for cmd, example in EXAMPLES.items():
        print(f"  {cmd}: {example}")
    
    print("\n🔗 Примеры ссылок для мониторинга:")
    for i, url in enumerate(SAMPLE_URLS, 1):
        print(f"  {i}. {url}")
    
    print("\n💬 Примеры ответов бота:")
    print("  Приветствие:")
    print(BOT_RESPONSES["welcome"][:100] + "...")
    
    print("\n  Уведомление о новых событиях:")
    print(BOT_RESPONSES["notification_example"][:100] + "...")
    
    print("\n🔍 Примеры селекторов:")
    for category, selectors in SELECTOR_EXAMPLES.items():
        print(f"  {category}: {', '.join(selectors[:3])}...")

if __name__ == "__main__":
    print_examples()