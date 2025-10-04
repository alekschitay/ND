#!/usr/bin/env python3
"""
Простой HTTP сервер для демонстрации Concert Monitor
Работает без внешних зависимостей
"""

import http.server
import socketserver
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs

class ConcertMonitorHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_demo()
        elif self.path == '/api/sites':
            self.serve_api_sites()
        elif self.path == '/api/events':
            self.serve_api_events()
        elif self.path == '/health':
            self.serve_health()
        else:
            super().do_GET()
    
    def serve_demo(self):
        """Подача демо HTML страницы"""
        try:
            with open('demo.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "Demo file not found")
    
    def serve_api_sites(self):
        """API для получения списка сайтов"""
        sites = [
            {
                "id": 1,
                "name": "Крокус Сити Холл",
                "url": "https://kroсus-city-hall.ru/events",
                "selector": ".event-card",
                "is_active": True,
                "created_at": "2024-10-04T12:00:00"
            },
            {
                "id": 2,
                "name": "Олимпийский",
                "url": "https://olympic-stadium.ru/concerts",
                "selector": ".concert-item",
                "is_active": True,
                "created_at": "2024-10-04T12:00:00"
            },
            {
                "id": 3,
                "name": "СК Олимпийский",
                "url": "https://olympic.ru/events",
                "selector": ".event-block",
                "is_active": True,
                "created_at": "2024-10-04T12:00:00"
            }
        ]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(sites, ensure_ascii=False).encode('utf-8'))
    
    def serve_api_events(self):
        """API для получения списка событий"""
        events = [
            {
                "id": 1,
                "site_id": 1,
                "title": "Концерт группы 'Ария'",
                "url": "https://kroсus-city-hall.ru/event/aria-2024",
                "date": "2024-12-15T20:00:00",
                "description": "Легендарная группа Ария выступит с новой программой",
                "is_new": True,
                "created_at": "2024-10-04T12:45:00",
                "site": {
                    "id": 1,
                    "name": "Крокус Сити Холл"
                }
            },
            {
                "id": 2,
                "site_id": 2,
                "title": "Рок-фестиваль 'Нашествие'",
                "url": "https://olympic-stadium.ru/event/nashestvie-2024",
                "date": "2024-12-20T19:00:00",
                "description": "Крупнейший рок-фестиваль России",
                "is_new": True,
                "created_at": "2024-10-04T12:45:00",
                "site": {
                    "id": 2,
                    "name": "Олимпийский"
                }
            },
            {
                "id": 3,
                "site_id": 3,
                "title": "Концерт 'Сплин'",
                "url": "https://olympic.ru/event/splin-2024",
                "date": "2024-12-25T21:00:00",
                "description": "Акустический концерт группы Сплин",
                "is_new": False,
                "created_at": "2024-10-03T15:30:00",
                "site": {
                    "id": 3,
                    "name": "СК Олимпийский"
                }
            }
        ]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(events, ensure_ascii=False).encode('utf-8'))
    
    def serve_health(self):
        """Health check endpoint"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "sites_count": 3,
            "events_count": 3,
            "new_events_count": 2
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health_data).encode('utf-8'))

def main():
    PORT = 8000
    
    print("🎵 Concert Monitor - Запуск демо сервера...")
    print(f"📱 Веб-интерфейс: http://localhost:{PORT}")
    print(f"📚 API документация: http://localhost:{PORT}/api/sites")
    print(f"🔍 Health check: http://localhost:{PORT}/health")
    print("\nНажмите Ctrl+C для остановки сервера")
    
    with socketserver.TCPServer(("", PORT), ConcertMonitorHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Сервер остановлен")

if __name__ == "__main__":
    main()