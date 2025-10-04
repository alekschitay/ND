"""
Конфигурации селекторов для популярных сайтов концертных площадок
"""

SITE_CONFIGS = {
    'kudago.com': {
        'name': 'KudaGo',
        'event_selector': '.poster-card, .event-card, .poster',
        'title_selector': '.poster-card__title, .event-card__title, h3, h2',
        'date_selector': '.poster-card__date, .event-card__date, .date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Популярный сайт с афишей событий'
    },
    
    'afisha.ru': {
        'name': 'Афиша',
        'event_selector': '.event-card, .poster-card, .event',
        'title_selector': '.event-card__title, .poster-card__title, h3',
        'date_selector': '.event-card__date, .poster-card__date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Классический сайт афиши'
    },
    
    'concert.ru': {
        'name': 'Concert.ru',
        'event_selector': '.event-item, .concert-item, .event',
        'title_selector': '.event-title, .concert-title, h3',
        'date_selector': '.event-date, .concert-date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Сайт концертных событий'
    },
    
    'ticketland.ru': {
        'name': 'Ticketland',
        'event_selector': '.event-card, .poster-card',
        'title_selector': '.event-title, .poster-title',
        'date_selector': '.event-date, .poster-date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Билетный оператор'
    },
    
    'pikabu.ru': {
        'name': 'Pikabu',
        'event_selector': '.story, .post',
        'title_selector': '.story__title, .post__title',
        'date_selector': '.story__date, .post__date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Социальная сеть с событиями'
    },
    
    'vk.com': {
        'name': 'VKontakte',
        'event_selector': '.post, .wall_item',
        'title_selector': '.post_title, .wall_item_title',
        'date_selector': '.post_date, .wall_item_date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Социальная сеть ВКонтакте'
    },
    
    'facebook.com': {
        'name': 'Facebook',
        'event_selector': '.event, .post',
        'title_selector': '.event-title, .post-title',
        'date_selector': '.event-date, .post-date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Социальная сеть Facebook'
    },
    
    'instagram.com': {
        'name': 'Instagram',
        'event_selector': '.post, .media',
        'title_selector': '.post-caption, .media-caption',
        'date_selector': '.post-date, .media-date',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Социальная сеть Instagram'
    },
    
    # Специальные конфигурации для сайтов с графическими афишами
    'poster_site': {
        'name': 'Сайт с графическими афишами',
        'event_selector': 'img, .poster, .afisha, .event-image',
        'title_selector': 'img[alt], img[title]',
        'date_selector': '',  # Дата обычно в изображении
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Сайт с графическими афишами (без текстовых описаний)'
    },
    
    'memobar.ru': {
        'name': 'MemoBar',
        'event_selector': '#rec355567016 img, .t-popup__container img',
        'title_selector': 'img[alt], img[title]',
        'date_selector': '',  # Дата в изображении
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Сайт с графическими афишами концертов (блок афиш)'
    },
    
    'viagogo.com': {
        'name': 'Viagogo',
        'event_selector': '.event-item, .concert-item, [data-testid="event-card"], .event-card',
        'title_selector': '.event-title, .concert-title, h3, h4, [data-testid="event-title"]',
        'date_selector': '.event-date, .concert-date, .date, [data-testid="event-date"]',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Билетный оператор Viagogo'
    }
}

def get_config_for_domain(domain: str) -> dict:
    """Получение конфигурации для домена"""
    domain_lower = domain.lower()
    
    # Проверяем точное совпадение
    if domain_lower in SITE_CONFIGS:
        return SITE_CONFIGS[domain_lower]
    
    # Проверяем частичное совпадение
    for site_domain, config in SITE_CONFIGS.items():
        if site_domain in domain_lower:
            return config
    
    # Проверяем, является ли это сайтом с графическими афишами
    poster_keywords = ['poster', 'afisha', 'афиша', 'posters', 'events', 'concerts']
    if any(keyword in domain_lower for keyword in poster_keywords):
        return SITE_CONFIGS['poster_site']
    
    # Возвращаем общую конфигурацию
    return {
        'name': 'Unknown Site',
        'event_selector': '.event, .concert, .show, [class*="event"], [class*="concert"]',
        'title_selector': 'h1, h2, h3, .title, .name, .event-title',
        'date_selector': '.date, .time, .event-date, [class*="date"]',
        'link_selector': 'a',
        'image_selector': 'img',
        'description': 'Общая конфигурация'
    }

def list_supported_sites() -> list:
    """Список поддерживаемых сайтов"""
    return [
        {
            'domain': domain,
            'name': config['name'],
            'description': config['description']
        }
        for domain, config in SITE_CONFIGS.items()
    ]