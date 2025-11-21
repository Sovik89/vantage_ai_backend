"""
ScraperAPI LinkedIn Client
Handles LinkedIn profile scraping using ScraperAPI with rate limiting and retries.
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class LinkedInScraperClient:
    """Client for scraping LinkedIn profiles using ScraperAPI"""
    
    BASE_URL = "https://api.scraperapi.com"
    
    def __init__(self, api_key: str = None):
        """
        Initialize the ScraperAPI client
        
        Args:
            api_key: ScraperAPI key. Defaults to config.SCRAPERAPI_KEY
        """
        self.api_key = api_key or getattr(config, 'SCRAPERAPI_KEY', None)
        if not self.api_key:
            raise ValueError("ScraperAPI key not found. Set SCRAPERAPI_KEY in config.py")
        
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    def scrape_linkedin_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Scrape a LinkedIn profile and extract structured data
        
        Args:
            profile_url: Full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)
            
        Returns:
            Dictionary with profile data: name, headline, location, about, experience, education, skills
        """
        logger.info(f"Scraping LinkedIn profile: {profile_url}")
        
        # ScraperAPI parameters
        params = {
            'api_key': self.api_key,
            'url': profile_url,
            'render': 'true'  # Enable JavaScript rendering for dynamic content
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=60)
                response.raise_for_status()
                
                # Parse the HTML response
                html_content = response.text
                profile_data = self._parse_linkedin_html(html_content, profile_url)
                
                logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
                return profile_data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to scrape profile after {self.max_retries} attempts")
                    return self._create_error_profile(profile_url, str(e))
        
        return self._create_error_profile(profile_url, "Max retries exceeded")
    
    def scrape_multiple_profiles(self, profile_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple LinkedIn profiles with rate limiting
        
        Args:
            profile_urls: List of LinkedIn profile URLs
            
        Returns:
            List of profile data dictionaries
        """
        results = []
        total = len(profile_urls)
        
        for idx, url in enumerate(profile_urls, 1):
            logger.info(f"Processing profile {idx}/{total}")
            
            try:
                profile_data = self.scrape_linkedin_profile(url)
                results.append(profile_data)
                
                # Rate limiting: wait between requests
                if idx < total:
                    time.sleep(1)  # 1 second between requests
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                results.append(self._create_error_profile(url, str(e)))
        
        return results
    
    def _parse_linkedin_html(self, html: str, profile_url: str) -> Dict[str, Any]:
        """
        Parse LinkedIn HTML to extract structured profile data
        
        Note: This is a simplified parser. For production, consider using BeautifulSoup
        or a proper HTML parser to extract data more reliably.
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
            ('div', {'class': 'pv-text-details__left-panel'})
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                return element.get_text(strip=True)
        
        return "Unknown"
    
    def _extract_headline(self, soup) -> str:
        """Extract professional headline"""
        selectors = [
            ('div', {'class': 'text-body-medium'}),
            ('h2', {'class': 'top-card-layout__headline'})
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                return element.get_text(strip=True)
        
        return ""
    
    def _extract_location(self, soup) -> str:
        """Extract location"""
        location_elem = soup.find('span', {'class': 'text-body-small'})
        return location_elem.get_text(strip=True) if location_elem else ""
    
    def _extract_about(self, soup) -> str:
        """Extract about/summary section"""
        about_section = soup.find('section', {'id': 'about'})
        if about_section:
            return about_section.get_text(separator=' ', strip=True)
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
        open_to_work: bool = False
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
            
        Returns:
            List of LinkedIn profile URLs
        """
        logger.info(f"Searching LinkedIn for: {job_title} in {location}")
        
        # NOTE: LinkedIn search is blocked by anti-scraping protections
        # For trial/development, recommend using US locations or direct profile URLs
        logger.warning("⚠️  LinkedIn search may not work due to anti-scraping protections")
        logger.warning("⚠️  For better results, use direct LinkedIn profile URLs instead")
        
        # Build LinkedIn People Search URL
        # Format: https://www.linkedin.com/search/results/people/?keywords={keywords}&location={location}
        search_keywords = job_title.replace(' ', '%20')
        location_query = location.replace(' ', '%20').replace(',', '%2C')
        
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_keywords}&location={location_query}"
        
        # Add open to work filter if requested
        if open_to_work:
            search_url += "&openToWork=true"
        
        logger.info(f"LinkedIn search URL: {search_url}")
        
        # ScraperAPI parameters - try without render first (faster, less likely to be blocked)
        params = {
            'api_key': self.api_key,
            'url': search_url,
            'render': 'false'  # Try without JavaScript rendering first
        }
        
        profile_urls = []
        
        try:
            logger.info("Attempting LinkedIn search (this may fail due to LinkedIn's anti-bot protections)...")
            response = self.session.get(self.BASE_URL, params=params, timeout=90)
            
            # Log response details for debugging
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Parse search results HTML
            html_content = response.text
            profile_urls = self._extract_profile_urls_from_search(html_content, num_candidates)
            
            # Filter by experience if specified
            if min_experience is not None or max_experience is not None:
                logger.info(f"Experience filter will be applied during analysis phase")
                # Note: Experience filtering is done after scraping individual profiles
                # as LinkedIn search doesn't expose detailed experience filters in HTML
            
            logger.info(f"Found {len(profile_urls)} candidate profiles")
            
        except Exception as e:
            logger.error(f"LinkedIn search failed: {str(e)}")
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
        
        # LinkedIn search results typically have links with /in/ in the URL
        # Look for all links that match the pattern
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            
            # Match LinkedIn profile URLs: /in/username or /in/username/
            if '/in/' in href and '/search/' not in href:
                # Clean up the URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"https://www.linkedin.com{href}"
                else:
                    continue
                
                # Remove query parameters and fragments
                clean_url = re.sub(r'[?#].*$', '', full_url)
                
                # Ensure it's a valid profile URL format
                if re.match(r'https://www\.linkedin\.com/in/[^/]+/?$', clean_url):
                    if clean_url not in profile_urls:
                        profile_urls.append(clean_url)
                        
                        if len(profile_urls) >= max_results:
                            break
        
        logger.info(f"Extracted {len(profile_urls)} profile URLs from search results")
        return profile_urls

    def _create_error_profile(self, profile_url: str, error_message: str) -> Dict[str, Any]:
        """Create an error profile data structure"""
        return {
            'profile_url': profile_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'name': 'Error - Could not scrape',
            'headline': '',
            'location': '',
            'about': '',
            'experience': [],
            'education': [],
            'skills': [],
            'raw_text': f'Error: {error_message}',
            'error': error_message
        }


# Convenience function for single profile scraping
def scrape_linkedin_profile(profile_url: str) -> Dict[str, Any]:
    """
    Scrape a single LinkedIn profile
    
    Args:
        profile_url: LinkedIn profile URL
        
    Returns:
        Profile data dictionary
    """
    client = LinkedInScraperClient()
    return client.scrape_linkedin_profile(profile_url)


# Convenience function for batch scraping
def scrape_linkedin_profiles(profile_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape multiple LinkedIn profiles
    
    Args:
        profile_urls: List of LinkedIn profile URLs
        
    Returns:
        List of profile data dictionaries
    """
    client = LinkedInScraperClient()
    return client.scrape_multiple_profiles(profile_urls)


# Convenience function for LinkedIn search
def search_linkedin_candidates(
    job_title: str,
    location: str,
    num_candidates: int = 10,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    open_to_work: bool = False
) -> List[str]:
    """
    Search LinkedIn for candidate profile URLs
    
    Args:
        job_title: Job title or keywords
        location: Geographic location
        num_candidates: Number of candidates to find
        min_experience: Minimum years of experience
        max_experience: Maximum years of experience
        open_to_work: Filter for "Open to Work" candidates
        
    Returns:
        List of LinkedIn profile URLs
    """
    client = LinkedInScraperClient()
    return client.search_linkedin_candidates(
        job_title=job_title,
        location=location,
        num_candidates=num_candidates,
        min_experience=min_experience,
        max_experience=max_experience,
        open_to_work=open_to_work
    )
