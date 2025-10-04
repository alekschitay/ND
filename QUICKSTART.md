# Concert Monitor - Быстрый старт

## 🎯 Что делает система

Concert Monitor автоматически мониторит сайты концертных площадок и отправляет уведомления только при появлении новых событий.

### Основные возможности:
- ✅ Мониторинг сайтов каждые 10 минут
- ✅ Уведомления в Telegram и по email
- ✅ Поддержка графических афиш
- ✅ Веб-интерфейс для управления
- ✅ Гибкие CSS селекторы для любых сайтов

## 🚀 Быстрый запуск

### 1. Клонирование и настройка
```bash
git clone <repository-url>
cd concert-monitor
cp .env.example .env
```

### 2. Настройка .env файла
```env
# Telegram Bot (обязательно)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Email (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com

# Безопасность
SECRET_KEY=your_secret_key_change_this
```

### 3. Запуск с Docker
```bash
docker-compose up -d
```

### 4. Открыть веб-интерфейс
http://localhost:8000

## 📱 Настройка Telegram бота

1. **Создайте бота:**
   - Напишите [@BotFather](https://t.me/botfather)
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Сохраните токен

2. **Получите Chat ID:**
   - Напишите боту `/start`
   - Перейдите: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Найдите `chat.id` в ответе

## 🌐 Добавление сайта для мониторинга

1. Откройте веб-интерфейс
2. Нажмите "Добавить сайт"
3. Заполните форму:
   - **Название**: Крокус Сити Холл
   - **URL**: https://kroсus-city-hall.ru/events
   - **Селектор**: `.event-card`

### Примеры CSS селекторов:
- `.event-item` - элементы с классом event-item
- `.concert-card` - карточки концертов
- `div.event` - div элементы с классом event
- `li[class*="event"]` - li элементы содержащие "event"

## 📊 API Endpoints

- `GET /` - Главная страница
- `GET /api/sites` - Список сайтов
- `POST /api/sites` - Добавить сайт
- `GET /api/events` - Список событий
- `POST /api/check/{site_id}` - Проверить сайт
- `GET /docs` - Документация API

## 🔧 Структура проекта

```
concert-monitor/
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── scraper.py           # Веб-скрапер
│   ├── notifications.py     # Уведомления
│   ├── monitor_service.py   # Основной сервис
│   └── scheduler.py         # Планировщик
├── templates/
│   └── index.html          # Веб-интерфейс
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 📝 Формат уведомлений

**Telegram:**
```
🎵 Новое событие!

Название: Концерт группы "Ария"
Дата: 15.12.2024 20:00
Ссылка: https://example.com/event/123
Описание: Описание события...

Источник: Крокус Сити Холл
```

**Email:** HTML-письмо с афишей и полной информацией

## 🐛 Решение проблем

### Сайт не мониторится
1. Проверьте доступность URL
2. Убедитесь в правильности CSS селектора
3. Проверьте логи приложения

### Уведомления не приходят
1. Проверьте настройки Telegram бота
2. Убедитесь в правильности Chat ID
3. Проверьте настройки SMTP для email

### Ошибки скрапинга
1. Сайт может использовать JavaScript
2. Попробуйте другой CSS селектор
3. Проверьте robots.txt сайта

## 📈 Мониторинг

- Логи выводятся в консоль
- Статистика доступна в веб-интерфейсе
- Health check: `GET /health`

## 🔒 Безопасность

- Используйте сильный SECRET_KEY
- Настройте HTTPS в продакшене
- Ограничьте доступ к API
- Регулярно обновляйте зависимости

---

**Готово!** 🎉 Ваша система мониторинга концертных площадок готова к работе.