import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EventScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_chrome_driver(self):
        """Create Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    
    def scrape_events(self, url: str, selector: str) -> List[Dict]:
        """
        Scrape events from a website using CSS selector
        Returns list of event dictionaries
        """
        events = []
        
        try:
            # Try with requests first (faster)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            event_elements = soup.select(selector)
            
            if not event_elements:
                # If no elements found, try with Selenium (for JS-rendered content)
                logger.info(f"No elements found with requests, trying Selenium for {url}")
                events = self._scrape_with_selenium(url, selector)
            else:
                events = self._parse_events(event_elements, url)
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            # Fallback to Selenium
            try:
                events = self._scrape_with_selenium(url, selector)
            except Exception as selenium_error:
                logger.error(f"Selenium also failed for {url}: {str(selenium_error)}")
        
        return events
    
    def _scrape_with_selenium(self, url: str, selector: str) -> List[Dict]:
        """Scrape using Selenium for JavaScript-rendered content"""
        driver = None
        try:
            driver = self.get_chrome_driver()
            driver.get(url)
            
            # Wait for elements to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            event_elements = soup.select(selector)
            
            return self._parse_events(event_elements, url)
            
        finally:
            if driver:
                driver.quit()
    
    def _parse_events(self, event_elements, base_url: str) -> List[Dict]:
        """Parse event elements into structured data"""
        events = []
        
        for element in event_elements:
            try:
                event_data = self._extract_event_data(element, base_url)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.error(f"Error parsing event element: {str(e)}")
                continue
        
        return events
    
    def _extract_event_data(self, element, base_url: str) -> Optional[Dict]:
        """Extract event data from a single element"""
        try:
            # Extract title
            title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span'])
            title = title_element.get_text(strip=True) if title_element else ""
            
            if not title:
                return None
            
            # Extract URL
            url = ""
            link_element = element.find('a', href=True)
            if link_element:
                href = link_element['href']
                if href.startswith('http'):
                    url = href
                else:
                    url = self._make_absolute_url(href, base_url)
            else:
                # Try to find any link in the element
                link = element.find('a', href=True)
                if link:
                    href = link['href']
                    url = self._make_absolute_url(href, base_url) if not href.startswith('http') else href
            
            # Extract date
            date = self._extract_date(element)
            
            # Extract image
            image_url = self._extract_image(element, base_url)
            
            # Extract description
            description = self._extract_description(element)
            
            return {
                'title': title,
                'url': url,
                'date': date,
                'image_url': image_url,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error extracting event data: {str(e)}")
            return None
    
    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """Convert relative URL to absolute"""
        if url.startswith('http'):
            return url
        
        if url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
        
        return f"{base_url.rstrip('/')}/{url.lstrip('/')}"
    
    def _extract_date(self, element) -> Optional[datetime]:
        """Extract date from element"""
        # Look for common date patterns
        text = element.get_text()
        
        # Common date patterns
        date_patterns = [
            r'(\d{1,2})[./](\d{1,2})[./](\d{4})',  # DD/MM/YYYY or DD.MM.YYYY
            r'(\d{4})[./](\d{1,2})[./](\d{1,2})',  # YYYY/MM/DD or YYYY.MM.DD
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})',  # Russian months
        ]
        
        months_ru = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if 'января' in pattern:  # Russian format
                        day, month_name, year = match.groups()
                        month = months_ru[month_name.lower()]
                        return datetime(int(year), month, int(day))
                    else:
                        groups = match.groups()
                        if len(groups) == 3:
                            # Try different date formats
                            try:
                                if len(groups[0]) == 4:  # YYYY/MM/DD
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                                else:  # DD/MM/YYYY
                                    return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                            except ValueError:
                                continue
                except (ValueError, KeyError):
                    continue
        
        return None
    
    def _extract_image(self, element, base_url: str) -> Optional[str]:
        """Extract image URL from element"""
        img_element = element.find('img')
        if img_element and img_element.get('src'):
            src = img_element['src']
            return self._make_absolute_url(src, base_url)
        
        # Look for background images
        style = element.get('style', '')
        bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
        if bg_match:
            src = bg_match.group(1)
            return self._make_absolute_url(src, base_url)
        
        return None
    
    def _extract_description(self, element) -> Optional[str]:
        """Extract description from element"""
        # Look for description in various tags
        desc_tags = ['p', 'div', 'span']
        for tag in desc_tags:
            desc_element = element.find(tag)
            if desc_element:
                text = desc_element.get_text(strip=True)
                if len(text) > 10:  # Only if it's substantial text
                    return text[:500]  # Limit description length
        
        return None