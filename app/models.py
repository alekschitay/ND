from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class MonitoredSite(Base):
    __tablename__ = "monitored_sites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    selector = Column(String, nullable=False)  # CSS selector for events
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    events = relationship("Event", back_populates="site")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("monitored_sites.id"))
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    date = Column(DateTime, nullable=True)
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    is_new = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    site = relationship("MonitoredSite", back_populates="events")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    notification_type = Column(String, nullable=False)  # 'telegram', 'email'
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="sent")  # 'sent', 'failed'
    
    event = relationship("Event")