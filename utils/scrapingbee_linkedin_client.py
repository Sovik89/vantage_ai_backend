"""
ScrapingBee LinkedIn Client
Alternative to ScraperAPI with better LinkedIn support
"""

import requests
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import time
import config

logger = logging.getLogger(__name__)


class ScrapingBeeLinkedInClient:
    """
    Client for scraping LinkedIn profiles and searches using ScrapingBee
    ScrapingBee has better success rate with LinkedIn compared to ScraperAPI
    """
    
    BASE_URL = "https://app.scrapingbee.com/api/v1/"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.SCRAPINGBEE_API_KEY
        if not self.api_key:
            raise ValueError("ScrapingBee API key is required")
        
        self.session = requests.Session()
        self.max_retries = 3
        logger.info("ScrapingBee LinkedIn client initialized")
    
    def scrape_profile(self, profile_url: str) -> Dict:
        """
        Scrape a LinkedIn profile using ScrapingBee
        
        Args:
            profile_url: Full LinkedIn profile URL
            
        Returns:
            Dictionary with profile data
        """
        logger.info(f"Scraping LinkedIn profile with ScrapingBee: {profile_url}")
        
        params = {
            'api_key': self.api_key,
            'url': profile_url,
            'render_js': 'true',  # Enable JavaScript rendering
            'premium_proxy': 'true',  # Use premium proxies for LinkedIn
            'country_code': 'us'  # Use US proxy
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=90)
                response.raise_for_status()
                
                # Parse the HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract profile data
                profile_data = self._extract_profile_data(soup, profile_url)
                
                logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
                return profile_data
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logger.error(f"403 Forbidden - LinkedIn blocking (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                elif e.response.status_code == 429:
                    logger.error(f"Rate limit exceeded (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(10 * (attempt + 1))
                        continue
                raise
            except Exception as e:
                logger.error(f"Error scraping profile: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
        
        raise Exception(f"Failed to scrape profile after {self.max_retries} attempts")
    
    def search_linkedin_candidates(
        self,
        job_title: str,
        location: str,
        num_candidates: int = 10,
        open_to_work: bool = False
    ) -> List[str]:
        """
        Search LinkedIn for candidate profile URLs
        
        Args:
            job_title: Job title or keywords
            location: Geographic location
            num_candidates: Number of candidates to find
            open_to_work: Filter for "Open to Work" candidates
            
        Returns:
            List of LinkedIn profile URLs
        """
        logger.info(f"Searching LinkedIn with ScrapingBee: {job_title} in {location}")
        
        # Build LinkedIn People Search URL
        search_keywords = job_title.replace(' ', '%20')
        location_query = location.replace(' ', '%20').replace(',', '%2C')
        
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_keywords}&location={location_query}"
        
        if open_to_work:
            search_url += "&openToWork=true"
        
        logger.info(f"Search URL: {search_url}")
        
        params = {
            'api_key': self.api_key,
            'url': search_url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'country_code': 'us',
            'wait': '3000',  # Wait 3 seconds for content to load
            'block_resources': 'false'  # Load all resources including images
        }
        
        profile_urls = []
        
        try:
            logger.info("Attempting LinkedIn search with ScrapingBee premium proxies...")
            response = self.session.get(self.BASE_URL, params=params, timeout=120)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Credits used: {response.headers.get('spb-cost', 'Unknown')}")
            
            response.raise_for_status()
            
            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            profile_urls = self._extract_profile_urls_from_search(soup, num_candidates)
            
            logger.info(f"Found {len(profile_urls)} candidate profiles")
            return profile_urls
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error("LinkedIn search blocked despite premium proxies")
                logger.warning("Recommendation: Use direct LinkedIn profile URLs instead")
            else:
                logger.error(f"LinkedIn search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error during LinkedIn search: {e}")
            return []
    
    def _extract_profile_data(self, soup: BeautifulSoup, profile_url: str) -> Dict:
        """Extract structured data from LinkedIn profile HTML"""
        
        profile_data = {
            'profile_url': profile_url,
            'name': '',
            'headline': '',
            'location': '',
            'about': '',
            'experience': [],
            'education': [],
            'skills': []
        }
        
        try:
            # Extract name
            name_tag = soup.find('h1', class_=re.compile('text-heading-xlarge'))
            if name_tag:
                profile_data['name'] = name_tag.get_text(strip=True)
            
            # Extract headline
            headline_tag = soup.find('div', class_=re.compile('text-body-medium'))
            if headline_tag:
                profile_data['headline'] = headline_tag.get_text(strip=True)
            
            # Extract location
            location_tag = soup.find('span', class_=re.compile('text-body-small'))
            if location_tag:
                profile_data['location'] = location_tag.get_text(strip=True)
            
            # Extract about section
            about_section = soup.find('div', {'id': 'about'})
            if about_section:
                about_text = about_section.find_next('div', class_=re.compile('display-flex'))
                if about_text:
                    profile_data['about'] = about_text.get_text(strip=True)
            
            # Extract experience
            experience_section = soup.find('div', {'id': 'experience'})
            if experience_section:
                experience_items = experience_section.find_all('li', class_=re.compile('profile-section-card'))
                for item in experience_items[:5]:  # Limit to 5 most recent
                    exp_data = {
                        'title': '',
                        'company': '',
                        'duration': '',
                        'description': ''
                    }
                    
                    title_tag = item.find('div', class_=re.compile('display-flex.*align-items-center'))
                    if title_tag:
                        exp_data['title'] = title_tag.get_text(strip=True)
                    
                    profile_data['experience'].append(exp_data)
            
            # Extract skills
            skills_section = soup.find('div', {'id': 'skills'})
            if skills_section:
                skill_items = skills_section.find_all('div', class_=re.compile('hoverable-link-text'))
                profile_data['skills'] = [skill.get_text(strip=True) for skill in skill_items[:15]]
            
        except Exception as e:
            logger.warning(f"Error parsing profile data: {e}")
        
        return profile_data
    
    def _extract_profile_urls_from_search(self, soup: BeautifulSoup, max_urls: int) -> List[str]:
        """Extract profile URLs from LinkedIn search results"""
        
        profile_urls = []
        
        try:
            # Find all links that match LinkedIn profile URL pattern
            links = soup.find_all('a', href=re.compile(r'/in/[a-zA-Z0-9\-]+'))
            
            seen_profiles = set()
            for link in links:
                href = link.get('href', '')
                
                # Extract clean profile URL
                match = re.search(r'linkedin\.com/in/([a-zA-Z0-9\-]+)', href)
                if match:
                    profile_id = match.group(1)
                    profile_url = f"https://www.linkedin.com/in/{profile_id}/"
                    
                    if profile_url not in seen_profiles:
                        seen_profiles.add(profile_url)
                        profile_urls.append(profile_url)
                        
                        if len(profile_urls) >= max_urls:
                            break
            
        except Exception as e:
            logger.warning(f"Error extracting profile URLs: {e}")
        
        return profile_urls


# Convenience function
def scrape_linkedin_profiles(profile_urls: List[str]) -> List[Dict]:
    """
    Scrape multiple LinkedIn profiles using ScrapingBee
    
    Args:
        profile_urls: List of LinkedIn profile URLs
        
    Returns:
        List of profile data dictionaries
    """
    client = ScrapingBeeLinkedInClient()
    profiles = []
    
    for url in profile_urls:
        try:
            profile_data = client.scrape_profile(url)
            profiles.append(profile_data)
            time.sleep(2)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            continue
    
    return profiles


def search_linkedin_candidates(
    job_title: str,
    location: str,
    num_candidates: int = 10,
    open_to_work: bool = False
) -> List[str]:
    """
    Search LinkedIn for candidates using ScrapingBee
    
    Args:
        job_title: Job title to search for
        location: Location filter
        num_candidates: Number of candidates to find
        open_to_work: Filter for open to work candidates
        
    Returns:
        List of LinkedIn profile URLs
    """
    client = ScrapingBeeLinkedInClient()
    return client.search_linkedin_candidates(job_title, location, num_candidates, open_to_work)
