from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List

class MonitoredSiteCreate(BaseModel):
    name: str
    url: str
    selector: str

class MonitoredSiteUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    selector: Optional[str] = None
    is_active: Optional[bool] = None

class MonitoredSiteResponse(BaseModel):
    id: int
    name: str
    url: str
    selector: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    id: int
    site_id: int
    title: str
    url: str
    date: Optional[datetime]
    image_url: Optional[str]
    description: Optional[str]
    is_new: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventWithSite(EventResponse):
    site: MonitoredSiteResponse
    
    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    event_id: int
    notification_type: str
    sent_at: datetime
    status: str
    
    class Config:
        from_attributes = True