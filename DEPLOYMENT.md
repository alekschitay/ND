# 🚀 Развертывание телеграм-бота для мониторинга концертов

## 📋 Требования

- Python 3.8 или выше
- pip (менеджер пакетов Python)
- Токен Telegram бота
- Доступ к интернету

## 🛠 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd concert-monitor-bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка токена

Отредактируйте файл `config.py` или установите переменную окружения:

```bash
export BOT_TOKEN="ваш_токен_бота"
```

## 🏃‍♂️ Запуск

### Локальный запуск

```bash
python concert_monitor_bot.py
```

Или используйте скрипт:

```bash
./run_bot.sh
```

### Запуск в фоне

```bash
nohup python concert_monitor_bot.py > bot.log 2>&1 &
```

### Запуск с systemd (Linux)

1. Создайте файл сервиса `/etc/systemd/system/concert-bot.service`:

```ini
[Unit]
Description=Concert Monitor Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/concert-monitor-bot
ExecStart=/usr/bin/python3 /path/to/concert-monitor-bot/concert_monitor_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable concert-bot
sudo systemctl start concert-bot
```

3. Проверьте статус:

```bash
sudo systemctl status concert-bot
```

## 🐳 Docker развертывание

### 1. Создайте Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "concert_monitor_bot.py"]
```

### 2. Создайте docker-compose.yml

```yaml
version: '3.8'

services:
  concert-bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - MONITORING_INTERVAL=600
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 3. Запуск

```bash
docker-compose up -d
```

## ☁️ Облачное развертывание

### Heroku

1. Создайте `Procfile`:

```
worker: python concert_monitor_bot.py
```

2. Создайте `runtime.txt`:

```
python-3.9.7
```

3. Установите переменные окружения:

```bash
heroku config:set BOT_TOKEN=ваш_токен_бота
```

4. Разверните:

```bash
git push heroku main
```

### Railway

1. Подключите репозиторий к Railway
2. Установите переменную окружения `BOT_TOKEN`
3. Railway автоматически развернет приложение

### DigitalOcean App Platform

1. Создайте новое приложение
2. Подключите репозиторий
3. Установите переменные окружения
4. Настройте команду запуска: `python concert_monitor_bot.py`

## 🔧 Настройка

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | Обязательно |
| `MONITORING_INTERVAL` | Интервал мониторинга (сек) | 600 |
| `MAX_EVENTS_PER_NOTIFICATION` | Максимум событий в уведомлении | 5 |
| `MAX_IMAGES_PER_NOTIFICATION` | Максимум изображений | 3 |
| `HTTP_TIMEOUT` | Таймаут HTTP запросов | 30 |
| `LOG_LEVEL` | Уровень логирования | INFO |

### Настройка для конкретных сайтов

Добавьте в `config.py`:

```python
SITE_SPECIFIC_CONFIGS = {
    "example.com": {
        "event_selector": ".custom-event",
        "title_selector": ".custom-title",
        "date_selector": ".custom-date"
    }
}
```

## 📊 Мониторинг

### Логи

Бот ведет подробные логи:
- Информация о проверках
- Ошибки парсинга
- Статистика событий

### Проверка работы

```bash
# Проверка статуса (systemd)
sudo systemctl status concert-bot

# Проверка логов
tail -f bot.log

# Тестирование
python test_bot.py
```

## 🔒 Безопасность

### Рекомендации

1. **Не храните токен в коде** - используйте переменные окружения
2. **Ограничьте доступ** к файлам данных
3. **Регулярно обновляйте** зависимости
4. **Мониторьте логи** на предмет ошибок
5. **Используйте HTTPS** для веб-хуков (если применимо)

### Файлы данных

```bash
# Установите правильные права доступа
chmod 600 monitored_urls.json events_cache.json
chown your_user:your_group *.json
```

## 🚨 Устранение неполадок

### Бот не отвечает

1. Проверьте токен:
```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/getMe"
```

2. Проверьте логи:
```bash
tail -f bot.log
```

3. Проверьте интернет-соединение

### События не парсятся

1. Проверьте доступность сайта
2. Убедитесь, что сайт не блокирует ботов
3. Добавьте специфичные селекторы
4. Проверьте User-Agent в запросах

### Высокое потребление ресурсов

1. Увеличьте интервал мониторинга
2. Уменьшите количество элементов для парсинга
3. Ограничьте количество отслеживаемых URL

## 📈 Масштабирование

### Для большого количества пользователей

1. **Используйте базу данных** вместо JSON файлов
2. **Добавьте кэширование** для часто запрашиваемых страниц
3. **Используйте очереди** для обработки задач
4. **Разделите на микросервисы** (парсинг, уведомления, API)

### Пример с PostgreSQL

```python
import psycopg2
from sqlalchemy import create_engine

# Замените JSON файлы на базу данных
engine = create_engine('postgresql://user:pass@localhost/db')
```

## 🔄 Обновления

### Обновление кода

```bash
git pull origin main
pip install -r requirements.txt
sudo systemctl restart concert-bot
```

### Обновление зависимостей

```bash
pip install --upgrade -r requirements.txt
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи бота
2. Убедитесь в правильности настроек
3. Проверьте доступность отслеживаемых сайтов
4. Создайте issue в репозитории

## 📄 Лицензия

Этот проект создан для демонстрационных целей. Используйте на свой страх и риск.