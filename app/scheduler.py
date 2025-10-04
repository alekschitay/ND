import asyncio
import schedule
import time
import threading
from app.database import SessionLocal
from app.monitor_service import MonitorService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the monitoring scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        # Schedule the monitoring task
        schedule.every(settings.CHECK_INTERVAL_MINUTES).minutes.do(self._run_monitoring)
        
        # Start the scheduler in a separate thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info(f"Monitoring scheduler started. Checking every {settings.CHECK_INTERVAL_MINUTES} minutes.")
    
    def stop(self):
        """Stop the monitoring scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Monitoring scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _run_monitoring(self):
        """Run the monitoring task"""
        try:
            logger.info("Starting monitoring check...")
            
            # Create database session
            db = SessionLocal()
            try:
                # Create monitor service and check all sites
                monitor_service = MonitorService(db)
                monitor_service.check_all_sites()
                
                logger.info("Monitoring check completed successfully")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error during monitoring check: {str(e)}")
    
    def run_once(self):
        """Run monitoring check once (for testing)"""
        self._run_monitoring()

# Global scheduler instance
scheduler = MonitoringScheduler()