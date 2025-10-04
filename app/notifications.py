import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from telegram import Bot
from telegram.error import TelegramError
import requests
from io import BytesIO
from PIL import Image
from app.config import settings
from app.models import Event
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.telegram_bot = None
        if settings.TELEGRAM_BOT_TOKEN:
            self.telegram_bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    async def send_notification(self, event: Event, notification_type: str = "telegram"):
        """Send notification about new event"""
        try:
            if notification_type == "telegram":
                await self._send_telegram_notification(event)
            elif notification_type == "email":
                await self._send_email_notification(event)
        except Exception as e:
            logger.error(f"Failed to send {notification_type} notification: {str(e)}")
            raise
    
    async def _send_telegram_notification(self, event: Event):
        """Send Telegram notification"""
        if not self.telegram_bot or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram bot not configured")
            return
        
        try:
            message = self._format_telegram_message(event)
            
            # Send message
            await self.telegram_bot.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            
            # Send image if available
            if event.image_url:
                try:
                    await self._send_telegram_image(event.image_url, event.title)
                except Exception as img_error:
                    logger.warning(f"Failed to send image: {str(img_error)}")
            
            logger.info(f"Telegram notification sent for event: {event.title}")
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {str(e)}")
            raise
    
    async def _send_telegram_image(self, image_url: str, caption: str):
        """Send image to Telegram"""
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Create image file
            image_file = BytesIO(response.content)
            
            # Send image
            await self.telegram_bot.send_photo(
                chat_id=settings.TELEGRAM_CHAT_ID,
                photo=image_file,
                caption=caption[:1024]  # Telegram caption limit
            )
            
        except Exception as e:
            logger.error(f"Failed to send Telegram image: {str(e)}")
            raise
    
    async def _send_email_notification(self, event: Event):
        """Send email notification"""
        if not all([settings.SMTP_HOST, settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.EMAIL_FROM]):
            logger.warning("Email settings not configured")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Новое событие: {event.title}"
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = settings.EMAIL_FROM  # You can add recipient field to settings
            
            # Create HTML content
            html_content = self._format_email_html(event)
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add image if available
            if event.image_url:
                try:
                    image_data = self._download_image(event.image_url)
                    if image_data:
                        image_part = MIMEImage(image_data)
                        image_part.add_header('Content-ID', '<event_image>')
                        image_part.add_header('Content-Disposition', 'inline', filename='event_image.jpg')
                        msg.attach(image_part)
                except Exception as img_error:
                    logger.warning(f"Failed to attach image to email: {str(img_error)}")
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for event: {event.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise
    
    def _format_telegram_message(self, event: Event) -> str:
        """Format message for Telegram"""
        message = f"🎵 <b>Новое событие!</b>\n\n"
        message += f"<b>Название:</b> {event.title}\n"
        
        if event.date:
            message += f"<b>Дата:</b> {event.date.strftime('%d.%m.%Y %H:%M')}\n"
        
        if event.url:
            message += f"<b>Ссылка:</b> {event.url}\n"
        
        if event.description:
            message += f"<b>Описание:</b> {event.description[:300]}...\n" if len(event.description) > 300 else f"<b>Описание:</b> {event.description}\n"
        
        message += f"\n<b>Источник:</b> {event.site.name}"
        
        return message
    
    def _format_email_html(self, event: Event) -> str:
        """Format HTML content for email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .event-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .event-title {{ font-size: 24px; font-weight: bold; color: #333; margin-bottom: 10px; }}
                .event-date {{ color: #666; font-size: 16px; margin-bottom: 10px; }}
                .event-description {{ color: #555; line-height: 1.6; margin-bottom: 15px; }}
                .event-link {{ color: #007bff; text-decoration: none; }}
                .event-image {{ max-width: 100%; height: auto; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="event-card">
                <h1 class="event-title">🎵 {event.title}</h1>
        """
        
        if event.date:
            html += f'<div class="event-date">📅 {event.date.strftime("%d.%m.%Y %H:%M")}</div>'
        
        if event.image_url:
            html += f'<img src="cid:event_image" class="event-image" alt="{event.title}">'
        
        if event.description:
            html += f'<div class="event-description">{event.description}</div>'
        
        if event.url:
            html += f'<div><a href="{event.url}" class="event-link">🔗 Подробнее</a></div>'
        
        html += f"""
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; color: #888;">
                    Источник: {event.site.name}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _download_image(self, image_url: str) -> bytes:
        """Download image data"""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {str(e)}")
            return None