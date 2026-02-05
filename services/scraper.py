import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re

class WikipediaScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is a Wikipedia URL"""
        return 'wikipedia.org/wiki/' in url
    
    def scrape_article(self, url: str) -> Dict:
        """Scrape Wikipedia article and return structured data"""
        if not self.validate_url(url):
            raise ValueError("Invalid Wikipedia URL. URL must contain 'wikipedia.org/wiki/'")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Wikipedia page: {str(e)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        raw_html = str(soup)
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract summary
        summary = self._extract_summary(soup)
        
        # Extract sections
        sections = self._extract_sections(soup)
        
        # Extract key entities
        key_entities = self._extract_entities(soup)
        
        # Extract full text for LLM
        full_text = self._extract_full_text(soup)
        
        return {
            'title': title,
            'summary': summary,
            'sections': sections,
            'key_entities': key_entities,
            'raw_html': raw_html,
            'full_text': full_text
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        title = soup.find('h1', {'id': 'firstHeading'})
        return title.get_text(strip=True) if title else "Unknown"
    
    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract article summary (first few paragraphs)"""
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return ""
        
        # Get paragraphs before first heading
        paragraphs = []
        for element in content_div.find_all(['p', 'h2']):
            if element.name == 'h2':
                break
            if element.name == 'p' and element.get_text(strip=True):
                text = element.get_text(strip=True)
                # Remove citations
                text = re.sub(r'\[\d+\]', '', text)
                paragraphs.append(text)
        
        return ' '.join(paragraphs[:3]) if paragraphs else ""
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[str]:
        """Extract section headings"""
        sections = []
        for heading in soup.find_all(['h2', 'h3']):
            text = heading.get_text(strip=True)
            # Remove "[edit]" text
            text = re.sub(r'\[edit\]', '', text)
            if text and text not in ['Contents', 'See also', 'References', 'External links']:
                sections.append(text)
        return sections[:10]  # Limit to first 10 sections
    
    def _extract_entities(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract key entities from the article"""
        entities = {
            'people': [],
            'organizations': [],
            'locations': []
        }
        
        # Try to extract from infobox
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            # Look for birth place, death place (locations)
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header:
                    header_text = header.get_text(strip=True).lower()
                    if 'birth' in header_text or 'place' in header_text or 'location' in header_text:
                        data = row.find('td')
                        if data:
                            location = data.get_text(strip=True)
                            if location and location not in entities['locations']:
                                entities['locations'].append(location)
        
        # Extract from categories
        categories = soup.find_all('a', {'class': 'mw-normal-catlink'})
        for cat in categories:
            cat_text = cat.get_text(strip=True).lower()
            if 'people' in cat_text:
                # Try to extract person name from title
                title = self._extract_title(soup)
                if title and title not in entities['people']:
                    entities['people'].append(title)
        
        return entities
    
    def _extract_full_text(self, soup: BeautifulSoup) -> str:
        """Extract full article text for LLM processing"""
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return ""
        
        # Remove unwanted elements
        for unwanted in content_div.find_all(['table', 'sup', '.mw-editsection', 'script', 'style']):
            unwanted.decompose()
        
        # Get text
        text = content_div.get_text(separator='\n', strip=True)
        
        # Clean up
        text = re.sub(r'\[\d+\]', '', text)  # Remove citations
        text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
        
        # Limit to first 8000 characters to avoid token limits
        return text[:8000]