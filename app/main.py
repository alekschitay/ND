from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db, create_tables
from app.models import MonitoredSite, Event, Notification
from app.schemas import (
    MonitoredSiteCreate, MonitoredSiteUpdate, MonitoredSiteResponse,
    EventResponse, EventWithSite, NotificationResponse
)
from app.monitor_service import MonitorService
from app.scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Concert Monitor", description="Мониторинг концертных площадок")

# Create database tables
create_tables()

# Start scheduler
scheduler.start()

# Templates
templates = Jinja2Templates(directory="templates")

# API Routes
@app.get("/")
async def root(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/sites", response_model=List[MonitoredSiteResponse])
async def get_sites(db: Session = Depends(get_db)):
    """Get all monitored sites"""
    return db.query(MonitoredSite).all()

@app.post("/api/sites", response_model=MonitoredSiteResponse)
async def create_site(site_data: MonitoredSiteCreate, db: Session = Depends(get_db)):
    """Create a new monitored site"""
    # Check if site with this URL already exists
    existing_site = db.query(MonitoredSite).filter(MonitoredSite.url == site_data.url).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Site with this URL already exists")
    
    site = MonitoredSite(
        name=site_data.name,
        url=site_data.url,
        selector=site_data.selector,
        is_active=True
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site

@app.put("/api/sites/{site_id}", response_model=MonitoredSiteResponse)
async def update_site(site_id: int, site_data: MonitoredSiteUpdate, db: Session = Depends(get_db)):
    """Update a monitored site"""
    site = db.query(MonitoredSite).filter(MonitoredSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    for key, value in site_data.dict(exclude_unset=True).items():
        setattr(site, key, value)
    
    db.commit()
    db.refresh(site)
    return site

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: int, db: Session = Depends(get_db)):
    """Delete a monitored site"""
    site = db.query(MonitoredSite).filter(MonitoredSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Delete associated events
    db.query(Event).filter(Event.site_id == site_id).delete()
    
    # Delete the site
    db.delete(site)
    db.commit()
    return {"message": "Site deleted successfully"}

@app.get("/api/events", response_model=List[EventWithSite])
async def get_events(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent events"""
    events = db.query(Event).order_by(Event.created_at.desc()).limit(limit).all()
    return events

@app.get("/api/events/site/{site_id}", response_model=List[EventResponse])
async def get_events_by_site(site_id: int, db: Session = Depends(get_db)):
    """Get events for a specific site"""
    events = db.query(Event).filter(Event.site_id == site_id).order_by(Event.created_at.desc()).all()
    return events

@app.post("/api/check/{site_id}")
async def check_site_manually(site_id: int, db: Session = Depends(get_db)):
    """Manually check a specific site"""
    site = db.query(MonitoredSite).filter(MonitoredSite.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    try:
        monitor_service = MonitorService(db)
        monitor_service.check_site(site)
        return {"message": f"Site {site.name} checked successfully"}
    except Exception as e:
        logger.error(f"Error checking site {site.name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking site: {str(e)}")

@app.post("/api/check-all")
async def check_all_sites(db: Session = Depends(get_db)):
    """Manually check all sites"""
    try:
        monitor_service = MonitorService(db)
        monitor_service.check_all_sites()
        return {"message": "All sites checked successfully"}
    except Exception as e:
        logger.error(f"Error checking all sites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking sites: {str(e)}")

@app.get("/api/notifications", response_model=List[NotificationResponse])
async def get_notifications(limit: int = 100, db: Session = Depends(get_db)):
    """Get recent notifications"""
    notifications = db.query(Notification).order_by(Notification.sent_at.desc()).limit(limit).all()
    return notifications

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "scheduler_running": scheduler.running}

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    scheduler.stop()
    logger.info("Application shutdown complete")