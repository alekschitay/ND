#!/usr/bin/env python3
"""
Демо-версия Concert Monitor
Упрощенная версия без внешних зависимостей для демонстрации
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import os

# Создаем FastAPI приложение
app = FastAPI(title="Concert Monitor Demo", description="Демо версия мониторинга концертных площадок")

# Простые модели данных
class MonitoredSite(BaseModel):
    id: int
    name: str
    url: str
    selector: str
    is_active: bool = True
    created_at: datetime = datetime.now()

class Event(BaseModel):
    id: int
    site_id: int
    title: str
    url: str
    date: Optional[datetime] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_new: bool = True
    created_at: datetime = datetime.now()

# В памяти хранилище (в реальном приложении используется база данных)
sites_db = []
events_db = []
next_site_id = 1
next_event_id = 1

# Добавляем демо-данные
demo_sites = [
    MonitoredSite(
        id=1,
        name="Крокус Сити Холл",
        url="https://kroсus-city-hall.ru/events",
        selector=".event-card",
        is_active=True
    ),
    MonitoredSite(
        id=2,
        name="Олимпийский",
        url="https://olympic-stadium.ru/concerts",
        selector=".concert-item",
        is_active=True
    )
]

demo_events = [
    Event(
        id=1,
        site_id=1,
        title="Концерт группы 'Ария'",
        url="https://kroсus-city-hall.ru/event/aria-2024",
        date=datetime(2024, 12, 15, 20, 0),
        description="Легендарная группа Ария выступит с новой программой",
        is_new=True
    ),
    Event(
        id=2,
        site_id=2,
        title="Рок-фестиваль 'Нашествие'",
        url="https://olympic-stadium.ru/event/nashestvie-2024",
        date=datetime(2024, 12, 20, 19, 0),
        description="Крупнейший рок-фестиваль России",
        is_new=False
    )
]

sites_db.extend(demo_sites)
events_db.extend(demo_events)
next_site_id = 3
next_event_id = 3

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница с веб-интерфейсом"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Concert Monitor Demo</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            .event-card { transition: transform 0.2s; }
            .event-card:hover { transform: translateY(-2px); }
            .new-event { border-left: 4px solid #28a745; }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="fas fa-music"></i> Concert Monitor Demo
                </a>
            </div>
        </nav>

        <div class="container mt-4">
            <div class="row">
                <div class="col-12">
                    <h1><i class="fas fa-music"></i> Мониторинг концертных площадок</h1>
                    <p class="lead">Демо-версия системы мониторинга событий на сайтах концертных площадок</p>
                </div>
            </div>

            <!-- Статистика -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h4 id="totalSites">2</h4>
                                    <p class="mb-0">Мониторится сайтов</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-globe fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h4 id="totalEvents">2</h4>
                                    <p class="mb-0">Всего событий</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-calendar fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h4 id="newEvents">1</h4>
                                    <p class="mb-0">Новых событий</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-star fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h4 id="activeSites">2</h4>
                                    <p class="mb-0">Активных сайтов</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-check-circle fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Мониторимые сайты -->
            <div class="row mb-4">
                <div class="col-12">
                    <h2><i class="fas fa-globe"></i> Мониторимые сайты</h2>
                    <div class="card">
                        <div class="card-body">
                            <div class="card mb-3">
                                <div class="card-body">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div>
                                            <h5 class="card-title">
                                                <span class="badge bg-success me-2">Активен</span>
                                                Крокус Сити Холл
                                            </h5>
                                            <p class="card-text">
                                                <strong>URL:</strong> <a href="https://kroсus-city-hall.ru/events" target="_blank">https://kroсus-city-hall.ru/events</a><br>
                                                <strong>Селектор:</strong> <code>.event-card</code><br>
                                                <small class="text-muted">Добавлен: 04.10.2024 12:00</small>
                                            </p>
                                        </div>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary">
                                                <i class="fas fa-sync"></i> Проверить
                                            </button>
                                            <button class="btn btn-sm btn-outline-secondary">
                                                <i class="fas fa-edit"></i> Редактировать
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="card mb-3">
                                <div class="card-body">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div>
                                            <h5 class="card-title">
                                                <span class="badge bg-success me-2">Активен</span>
                                                Олимпийский
                                            </h5>
                                            <p class="card-text">
                                                <strong>URL:</strong> <a href="https://olympic-stadium.ru/concerts" target="_blank">https://olympic-stadium.ru/concerts</a><br>
                                                <strong>Селектор:</strong> <code>.concert-item</code><br>
                                                <small class="text-muted">Добавлен: 04.10.2024 12:00</small>
                                            </p>
                                        </div>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary">
                                                <i class="fas fa-sync"></i> Проверить
                                            </button>
                                            <button class="btn btn-sm btn-outline-secondary">
                                                <i class="fas fa-edit"></i> Редактировать
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- События -->
            <div class="row">
                <div class="col-12">
                    <h2><i class="fas fa-calendar"></i> Последние события</h2>
                    <div class="card">
                        <div class="card-body">
                            <div class="card mb-3 event-card new-event">
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-8">
                                            <h5 class="card-title">Концерт группы 'Ария'</h5>
                                            <p class="card-text">
                                                <strong>Сайт:</strong> Крокус Сити Холл<br>
                                                <strong>Дата:</strong> 15.12.2024 20:00<br>
                                                <strong>Описание:</strong> Легендарная группа Ария выступит с новой программой<br>
                                                <small class="text-muted">Найдено: 04.10.2024 12:00</small>
                                            </p>
                                            <a href="https://kroсus-city-hall.ru/event/aria-2024" target="_blank" class="btn btn-primary btn-sm">Подробнее</a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="card mb-3 event-card">
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-8">
                                            <h5 class="card-title">Рок-фестиваль 'Нашествие'</h5>
                                            <p class="card-text">
                                                <strong>Сайт:</strong> Олимпийский<br>
                                                <strong>Дата:</strong> 20.12.2024 19:00<br>
                                                <strong>Описание:</strong> Крупнейший рок-фестиваль России<br>
                                                <small class="text-muted">Найдено: 04.10.2024 12:00</small>
                                            </p>
                                            <a href="https://olympic-stadium.ru/event/nashestvie-2024" target="_blank" class="btn btn-primary btn-sm">Подробнее</a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Информация о демо -->
            <div class="row mt-4">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h4><i class="fas fa-info-circle"></i> О демо-версии</h4>
                        <p>Это демонстрационная версия системы мониторинга концертных площадок. В полной версии доступны:</p>
                        <ul>
                            <li>Реальный веб-скрапинг сайтов</li>
                            <li>Уведомления в Telegram и по email</li>
                            <li>Автоматический мониторинг каждые 10 минут</li>
                            <li>База данных для хранения событий</li>
                            <li>Полный API для управления</li>
                        </ul>
                        <p><strong>API Endpoints:</strong></p>
                        <ul>
                            <li><code>GET /api/sites</code> - Список сайтов</li>
                            <li><code>GET /api/events</code> - Список событий</li>
                            <li><code>POST /api/sites</code> - Добавить сайт</li>
                            <li><code>GET /docs</code> - Документация API</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/sites", response_model=List[MonitoredSite])
async def get_sites():
    """Получить список всех мониторимых сайтов"""
    return sites_db

@app.get("/api/events", response_model=List[Event])
async def get_events():
    """Получить список всех событий"""
    return events_db

@app.post("/api/sites", response_model=MonitoredSite)
async def create_site(site: MonitoredSite):
    """Создать новый мониторимый сайт"""
    global next_site_id
    site.id = next_site_id
    next_site_id += 1
    sites_db.append(site)
    return site

@app.get("/health")
async def health_check():
    """Проверка состояния приложения"""
    return {
        "status": "healthy",
        "sites_count": len(sites_db),
        "events_count": len(events_db),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    print("🎵 Запуск Concert Monitor Demo...")
    print("📱 Веб-интерфейс: http://localhost:8000")
    print("📚 API документация: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)