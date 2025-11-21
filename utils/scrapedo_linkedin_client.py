"""
Scrape.do LinkedIn Client
Handles LinkedIn profile scraping using Scrape.do API with better success rates.
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import quote
import config

logger = logging.getLogger(__name__)

class LinkedInScrapeDoClient:
    """Client for scraping LinkedIn profiles using Scrape.do API"""
    
    BASE_URL = "https://api.scrape.do"
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Scrape.do client
        
        Args:
            api_key: Scrape.do API token. Defaults to config.SCRAPEDO_API_KEY
        """
        self.api_key = api_key or getattr(config, 'SCRAPEDO_API_KEY', None)
        if not self.api_key:
            raise ValueError("Scrape.do API key not found. Set SCRAPEDO_API_KEY in config.py")
        
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    def scrape_linkedin_profile(self, profile_url: str, use_super_proxy: bool = False) -> Dict[str, Any]:
        """
        Scrape a LinkedIn profile and extract structured data
        
        Args:
            profile_url: Full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)
            use_super_proxy: Use residential/mobile proxies (costs 5x but higher success rate)
            
        Returns:
            Dictionary with profile data: name, headline, location, about, experience, education, skills
        """
        logger.info(f"Scraping LinkedIn profile: {profile_url}")
        
        # Scrape.do parameters
        # Note: render=true uses 5 concurrency units vs 1 for non-render
        params = {
            'token': self.api_key,
            'url': profile_url,
            'render': 'true',  # Enable JavaScript rendering for dynamic content
            'waitUntil': 'networkidle2',  # Wait until network is idle
            'customWait': 3000,  # Wait 3 seconds after page load
            'blockResources': 'true',  # Block CSS, images, fonts for faster loading
            'device': 'desktop',  # Use desktop user agent
            'timeout': 60000,  # 60 second timeout
        }
        
        # Add super proxy for better success rate with LinkedIn
        if use_super_proxy:
            params['super'] = 'true'  # Use residential & mobile proxy network
            params['geoCode'] = 'us'  # Target US location
            logger.info("Using residential/mobile proxies for better success rate")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} - Scraping profile...")
                response = self.session.get(self.BASE_URL, params=params, timeout=90)
                
                # Log response details for debugging
                logger.info(f"Response status: {response.status_code}")
                
                response.raise_for_status()
                
                # Parse the HTML response
                html_content = response.text
                profile_data = self._parse_linkedin_html(html_content, profile_url)
                
                logger.info(f"✅ Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
                return profile_data
                
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}")
                
                # On first failure, retry with super proxy if not already using it
                if attempt == 0 and not use_super_proxy:
                    logger.info("Retrying with residential proxy...")
                    params['super'] = 'true'
                    params['geoCode'] = 'us'
                    use_super_proxy = True
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to scrape profile after {self.max_retries} attempts")
                    return self._create_error_profile(profile_url, str(e))
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to scrape profile after {self.max_retries} attempts")
                    return self._create_error_profile(profile_url, str(e))
        
        return self._create_error_profile(profile_url, "Max retries exceeded")
    
    def scrape_multiple_profiles(self, profile_urls: List[str], use_super_proxy: bool = False) -> List[Dict[str, Any]]:
        """
        Scrape multiple LinkedIn profiles with rate limiting
        
        Args:
            profile_urls: List of LinkedIn profile URLs
            use_super_proxy: Use residential/mobile proxies for all requests
            
        Returns:
            List of profile data dictionaries
        """
        results = []
        total = len(profile_urls)
        
        for idx, url in enumerate(profile_urls, 1):
            logger.info(f"Processing profile {idx}/{total}")
            
            try:
                profile_data = self.scrape_linkedin_profile(url, use_super_proxy=use_super_proxy)
                results.append(profile_data)
                
                # Rate limiting: wait between requests
                if idx < total:
                    time.sleep(2)  # 2 seconds between requests to be respectful
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                results.append(self._create_error_profile(url, str(e)))
        
        return results
    
    def _parse_linkedin_html(self, html: str, profile_url: str) -> Dict[str, Any]:
        """
        Parse LinkedIn HTML to extract structured profile data
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        profile_data = {
            'profile_url': profile_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'name': self._extract_name(soup),
            'headline': self._extract_headline(soup),
            'location': self._extract_location(soup),
            'about': self._extract_about(soup),
            'experience': self._extract_experience(soup),
            'education': self._extract_education(soup),
            'skills': self._extract_skills(soup),
            'raw_text': soup.get_text(separator=' ', strip=True)[:5000]  # First 5000 chars
        }
        
        return profile_data
    
    def _extract_name(self, soup) -> str:
        """Extract full name from profile"""
        # Try multiple selectors
        selectors = [
            ('h1', {'class': 'text-heading-xlarge'}),
            ('h1', {'class': 'top-card-layout__title'}),
            ('div', {'class': 'pv-text-details__left-panel'}),
            ('h1', None)  # Fallback to any h1
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs) if attrs else soup.find(tag)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 2:  # Valid name
                    return name
        
        return "Unknown"
    
    def _extract_headline(self, soup) -> str:
        """Extract professional headline"""
        selectors = [
            ('div', {'class': 'text-body-medium'}),
            ('h2', {'class': 'top-card-layout__headline'}),
            ('div', {'class': 'pv-text-details__headline'})
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                headline = element.get_text(strip=True)
                if headline and len(headline) > 5:
                    return headline
        
        return ""
    
    def _extract_location(self, soup) -> str:
        """Extract location"""
        selectors = [
            ('span', {'class': 'text-body-small'}),
            ('span', {'class': 'top-card-layout__location'}),
            ('div', {'class': 'pv-text-details__location'})
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                location = element.get_text(strip=True)
                if location and len(location) > 2:
                    return location
        
        return ""
    
    def _extract_about(self, soup) -> str:
        """Extract about/summary section"""
        about_section = soup.find('section', {'id': 'about'})
        if about_section:
            return about_section.get_text(separator=' ', strip=True)
        
        # Try alternative selectors
        about_div = soup.find('div', {'class': 'pv-about-section'})
        if about_div:
            return about_div.get_text(separator=' ', strip=True)
        
        return ""
    
    def _extract_experience(self, soup) -> List[Dict[str, str]]:
        """Extract work experience"""
        experience_list = []
        experience_section = soup.find('section', {'id': 'experience'})
        
        if experience_section:
            # Find all experience items
            items = experience_section.find_all('li', {'class': 'artdeco-list__item'})
            
            for item in items[:5]:  # Limit to 5 most recent
                exp = {
                    'title': '',
                    'company': '',
                    'duration': '',
                    'description': ''
                }
                
                # Extract title
                title_elem = item.find('div', {'class': 'display-flex'})
                if title_elem:
                    exp['title'] = title_elem.get_text(strip=True)
                
                # Extract company
                company_elem = item.find('span', {'class': 't-14'})
                if company_elem:
                    exp['company'] = company_elem.get_text(strip=True)
                
                # Extract full text as description
                exp['description'] = item.get_text(separator=' ', strip=True)[:500]
                
                experience_list.append(exp)
        
        return experience_list
    
    def _extract_education(self, soup) -> List[Dict[str, str]]:
        """Extract education history"""
        education_list = []
        education_section = soup.find('section', {'id': 'education'})
        
        if education_section:
            items = education_section.find_all('li', {'class': 'artdeco-list__item'})
            
            for item in items[:3]:  # Limit to 3 most recent
                edu = {
                    'school': '',
                    'degree': '',
                    'field': '',
                    'years': ''
                }
                
                # Extract school name
                school_elem = item.find('span', {'class': 't-bold'})
                if school_elem:
                    edu['school'] = school_elem.get_text(strip=True)
                
                # Extract degree info
                edu['degree'] = item.get_text(separator=' ', strip=True)[:300]
                
                education_list.append(edu)
        
        return education_list
    
    def _extract_skills(self, soup) -> List[str]:
        """Extract skills"""
        skills = []
        skills_section = soup.find('section', {'id': 'skills'})
        
        if skills_section:
            skill_items = skills_section.find_all('span', {'class': 't-bold'})
            skills = [skill.get_text(strip=True) for skill in skill_items[:20]]  # Top 20 skills
        
        return skills
    
    def search_linkedin_candidates(
        self,
        job_title: str,
        location: str,
        num_candidates: int = 10,
        min_experience: Optional[int] = None,
        max_experience: Optional[int] = None,
        open_to_work: bool = False,
        use_super_proxy: bool = True  # Default to True for search as it's more reliable
    ) -> List[str]:
        """
        Search LinkedIn for candidate profile URLs matching criteria
        
        Args:
            job_title: Job title or keywords to search for
            location: Geographic location (e.g., "San Francisco, CA", "Remote")
            num_candidates: Number of candidate URLs to return
            min_experience: Minimum years of experience
            max_experience: Maximum years of experience
            open_to_work: Filter for candidates marked as "Open to Work"
            use_super_proxy: Use residential/mobile proxies (recommended for LinkedIn)
            
        Returns:
            List of LinkedIn profile URLs
        """
        logger.info(f"🔍 Searching LinkedIn for: {job_title} in {location}")
        
        # Build LinkedIn People Search URL
        search_keywords = quote(job_title)
        location_query = quote(location)
        
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_keywords}&location={location_query}"
        
        # Add open to work filter if requested
        if open_to_work:
            search_url += "&openToWork=true"
        
        logger.info(f"LinkedIn search URL: {search_url}")
        
        # Scrape.do parameters for search
        params = {
            'token': self.api_key,
            'url': search_url,
            'render': 'true',  # Must render for LinkedIn search
            'waitUntil': 'networkidle2',
            'customWait': 5000,  # Wait 5 seconds for search results to load
            'blockResources': 'true',
            'device': 'desktop',
            'timeout': 90000,  # 90 seconds for search
        }
        
        # Use super proxy for better success with LinkedIn
        if use_super_proxy:
            params['super'] = 'true'
            params['geoCode'] = 'us'
            logger.info("Using residential/mobile proxies for LinkedIn search")
        
        profile_urls = []
        
        try:
            logger.info("Attempting LinkedIn search...")
            response = self.session.get(self.BASE_URL, params=params, timeout=120)
            
            logger.info(f"Response status: {response.status_code}")
            response.raise_for_status()
            
            # Parse search results HTML
            html_content = response.text
            profile_urls = self._extract_profile_urls_from_search(html_content, num_candidates)
            
            logger.info(f"✅ Found {len(profile_urls)} candidate profiles")
            
        except Exception as e:
            logger.error(f"❌ LinkedIn search failed: {str(e)}")
            # Return empty list on error - the router will handle this gracefully
        
        return profile_urls[:num_candidates]
    
    def _extract_profile_urls_from_search(self, html: str, max_results: int) -> List[str]:
        """
        Extract profile URLs from LinkedIn search results HTML
        
        Args:
            html: HTML content from LinkedIn search page
            max_results: Maximum number of URLs to extract
            
        Returns:
            List of LinkedIn profile URLs
        """
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(html, 'html.parser')
        profile_urls = []
        seen_urls = set()
        
        # LinkedIn search results typically have links with /in/ in the URL
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            
            # Match LinkedIn profile URLs
            # Pattern: /in/username or /in/username/
            if '/in/' in href and 'linkedin.com/in/' in href:
                # Extract the profile URL
                match = re.search(r'(https://[^/]*linkedin\.com/in/[^/?]+)', href)
                if match:
                    profile_url = match.group(1)
                    
                    # Avoid duplicates
                    if profile_url not in seen_urls:
                        seen_urls.add(profile_url)
                        profile_urls.append(profile_url)
                        
                        if len(profile_urls) >= max_results:
                            break
        
        return profile_urls
    
    def _create_error_profile(self, profile_url: str, error_message: str) -> Dict[str, Any]:
        """Create an error profile data dictionary"""
        return {
            'profile_url': profile_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'name': 'Error',
            'headline': '',
            'location': '',
            'about': '',
            'experience': [],
            'education': [],
            'skills': [],
            'raw_text': '',
            'error': error_message
        }


# Helper functions for router integration
def scrape_linkedin_profiles(profile_urls: List[str], use_super_proxy: bool = False) -> List[Dict[str, Any]]:
    """
    Scrape multiple LinkedIn profiles
    
    Args:
        profile_urls: List of LinkedIn profile URLs
        use_super_proxy: Use residential/mobile proxies
        
    Returns:
        List of profile data dictionaries
    """
    client = LinkedInScrapeDoClient()
    return client.scrape_multiple_profiles(profile_urls, use_super_proxy=use_super_proxy)


def search_linkedin_candidates(
    job_title: str,
    location: str,
    num_candidates: int = 10,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    open_to_work: bool = False,
    use_super_proxy: bool = True
) -> List[str]:
    """
    Search LinkedIn for candidate profiles
    
    Args:
        job_title: Job title or keywords
        location: Geographic location
        num_candidates: Number of candidates to find
        min_experience: Minimum years of experience
        max_experience: Maximum years of experience
        open_to_work: Filter for open to work candidates
        use_super_proxy: Use residential/mobile proxies
        
    Returns:
        List of LinkedIn profile URLs
    """
    client = LinkedInScrapeDoClient()
    return client.search_linkedin_candidates(
        job_title=job_title,
        location=location,
        num_candidates=num_candidates,
        min_experience=min_experience,
        max_experience=max_experience,
        open_to_work=open_to_work,
        use_super_proxy=use_super_proxy
    )


# Test function
if __name__ == "__main__":
    # Test with a public LinkedIn profile
    client = LinkedInScrapeDoClient()
    
    # Test profile scraping
    test_url = "https://www.linkedin.com/in/williamhgates/"
    profile = client.scrape_linkedin_profile(test_url, use_super_proxy=True)
    print(f"Profile: {profile.get('name')}")
    print(f"Headline: {profile.get('headline')}")
    print(f"Location: {profile.get('location')}")
