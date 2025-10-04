from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import MonitoredSite, Event, Notification
from app.scraper import EventScraper
from app.notifications import NotificationService
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)

class MonitorService:
    def __init__(self, db: Session):
        self.db = db
        self.scraper = EventScraper()
        self.notification_service = NotificationService()
    
    def check_all_sites(self):
        """Check all active monitored sites for new events"""
        sites = self.db.query(MonitoredSite).filter(MonitoredSite.is_active == True).all()
        
        for site in sites:
            try:
                logger.info(f"Checking site: {site.name} ({site.url})")
                self.check_site(site)
            except Exception as e:
                logger.error(f"Error checking site {site.name}: {str(e)}")
                continue
    
    def check_site(self, site: MonitoredSite):
        """Check a specific site for new events"""
        try:
            # Scrape events from the site
            scraped_events = self.scraper.scrape_events(site.url, site.selector)
            
            # Process each scraped event
            for event_data in scraped_events:
                self._process_event(site, event_data)
            
            # Update site's last check time
            site.updated_at = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error checking site {site.name}: {str(e)}")
            self.db.rollback()
            raise
    
    def _process_event(self, site: MonitoredSite, event_data: dict):
        """Process a single event and check if it's new"""
        try:
            # Create a unique identifier for the event
            event_hash = self._create_event_hash(event_data)
            
            # Check if this event already exists
            existing_event = self.db.query(Event).filter(
                and_(
                    Event.site_id == site.id,
                    Event.title == event_data['title'],
                    Event.url == event_data['url']
                )
            ).first()
            
            if existing_event:
                # Event already exists, mark as not new
                existing_event.is_new = False
                return
            
            # Create new event
            new_event = Event(
                site_id=site.id,
                title=event_data['title'],
                url=event_data['url'],
                date=event_data.get('date'),
                image_url=event_data.get('image_url'),
                description=event_data.get('description'),
                is_new=True
            )
            
            self.db.add(new_event)
            self.db.flush()  # Get the ID
            
            # Send notifications
            self._send_notifications(new_event)
            
            logger.info(f"New event found: {new_event.title} from {site.name}")
            
        except Exception as e:
            logger.error(f"Error processing event {event_data.get('title', 'Unknown')}: {str(e)}")
            self.db.rollback()
            raise
    
    def _create_event_hash(self, event_data: dict) -> str:
        """Create a hash for event identification"""
        # Use title and URL to create a unique identifier
        content = f"{event_data['title']}|{event_data['url']}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _send_notifications(self, event: Event):
        """Send notifications for a new event"""
        try:
            # Send Telegram notification
            if self.notification_service.telegram_bot:
                await self.notification_service.send_notification(event, "telegram")
                
                # Record notification
                notification = Notification(
                    event_id=event.id,
                    notification_type="telegram",
                    status="sent"
                )
                self.db.add(notification)
            
            # Send email notification
            if self.notification_service._send_email_notification:
                await self.notification_service.send_notification(event, "email")
                
                # Record notification
                notification = Notification(
                    event_id=event.id,
                    notification_type="email",
                    status="sent"
                )
                self.db.add(notification)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error sending notifications for event {event.title}: {str(e)}")
            # Record failed notification
            notification = Notification(
                event_id=event.id,
                notification_type="telegram",
                status="failed"
            )
            self.db.add(notification)
            self.db.commit()
    
    def get_recent_events(self, limit: int = 50) -> list:
        """Get recent events"""
        return self.db.query(Event).order_by(Event.created_at.desc()).limit(limit).all()
    
    def get_events_by_site(self, site_id: int) -> list:
        """Get events for a specific site"""
        return self.db.query(Event).filter(Event.site_id == site_id).order_by(Event.created_at.desc()).all()
    
    def add_monitored_site(self, name: str, url: str, selector: str) -> MonitoredSite:
        """Add a new site to monitor"""
        site = MonitoredSite(
            name=name,
            url=url,
            selector=selector,
            is_active=True
        )
        self.db.add(site)
        self.db.commit()
        return site
    
    def update_monitored_site(self, site_id: int, **kwargs) -> MonitoredSite:
        """Update a monitored site"""
        site = self.db.query(MonitoredSite).filter(MonitoredSite.id == site_id).first()
        if not site:
            raise ValueError(f"Site with id {site_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(site, key):
                setattr(site, key, value)
        
        self.db.commit()
        return site
    
    def delete_monitored_site(self, site_id: int) -> bool:
        """Delete a monitored site"""
        site = self.db.query(MonitoredSite).filter(MonitoredSite.id == site_id).first()
        if not site:
            return False
        
        # Delete associated events
        self.db.query(Event).filter(Event.site_id == site_id).delete()
        
        # Delete the site
        self.db.delete(site)
        self.db.commit()
        return True