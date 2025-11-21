"""
RapidAPI LinkedIn Client
Handles LinkedIn profile scraping using RapidAPI's Real-Time LinkedIn Scraper API
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class LinkedInRapidAPIClient:
    """Client for scraping LinkedIn profiles using RapidAPI"""
    
    BASE_URL = "https://linkedin-data-api.p.rapidapi.com"
    
    def __init__(self, api_key: str = None):
        """
        Initialize the RapidAPI client
        
        Args:
            api_key: RapidAPI key. Defaults to config.RAPIDAPI_KEY
        """
        self.api_key = api_key or getattr(config, 'RAPIDAPI_KEY', None)
        if not self.api_key:
            raise ValueError("RapidAPI key not found. Set RAPIDAPI_KEY in config.py")
        
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'linkedin-data-api.p.rapidapi.com'
        }
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    def scrape_linkedin_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Scrape a LinkedIn profile by URL
        
        Args:
            profile_url: Full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)
            
        Returns:
            Dictionary with profile data
        """
        logger.info(f"Scraping LinkedIn profile via RapidAPI: {profile_url}")
        
        # Extract username from URL
        username = self._extract_username_from_url(profile_url)
        
        # Correct endpoint - try getProfile first
        endpoint = f"{self.BASE_URL}/getProfile"
        
        # Build POST payload with URL
        payload = {"url": profile_url}
        headers_with_content = self.headers.copy()
        headers_with_content['content-type'] = 'application/json'
        
        for attempt in range(self.max_retries):
            try:
                # Use POST for profile endpoint
                response = self.session.post(
                    endpoint,
                    json=payload,
                    headers=headers_with_content,
                    timeout=30
                )
                
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                logger.info(f"Response data keys: {list(data.keys())}")
                
                profile_data = self._parse_rapidapi_response(data, profile_url)
                
                logger.info(f"✅ Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
                return profile_data
                
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return self._create_error_profile(profile_url, str(e))
                    
            except Exception as e:
                logger.warning(f"Error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
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
    
    def search_linkedin_people(
        self,
        keywords: str,
        location: str = None,
        limit: int = 10,
        open_to_work: bool = False
    ) -> List[str]:
        """
        Search LinkedIn for people using POST endpoint
        
        Args:
            keywords: Search keywords (job title, skills, etc.)
            location: Location filter
            limit: Number of results to return
            open_to_work: Filter for open to work candidates
            
        Returns:
            List of LinkedIn profile URLs
        """
        logger.info(f"🔍 Searching LinkedIn via RapidAPI (POST): {keywords}")
        
        # Correct endpoint for POST search
        endpoint = f"{self.BASE_URL}/searchPeople"
        
        # Build POST body
        payload = {
            "keywords": keywords,
            "page": 1,
            "count": limit
        }
        
        if location:
            payload["location"] = location
        
        if open_to_work:
            payload["openToWork"] = True
        
        # Add content-type header for POST
        headers = self.headers.copy()
        headers['content-type'] = 'application/json'
        
        try:
            logger.info(f"POST payload: {payload}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"Response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Response data keys: {list(data.keys())}")
            
            profile_urls = self._extract_profile_urls_from_search(data)
            
            logger.info(f"✅ Found {len(profile_urls)} profiles")
            return profile_urls[:limit]
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return []
    
    def _extract_username_from_url(self, profile_url: str) -> str:
        """Extract LinkedIn username from URL"""
        # https://www.linkedin.com/in/username/ -> username
        parts = profile_url.rstrip('/').split('/')
        if '/in/' in profile_url:
            return parts[-1]
        return ""
    
    def _parse_rapidapi_response(self, data: Dict, profile_url: str) -> Dict[str, Any]:
        """
        Parse RapidAPI response into our standard format
        
        Args:
            data: Raw response from RapidAPI
            profile_url: Original profile URL
            
        Returns:
            Standardized profile data dictionary
        """
        # Handle different response structures - data might be nested under 'data' key
        if 'data' in data and isinstance(data['data'], dict):
            data = data['data']
        
        # Build name from available fields
        first_name = data.get('firstName', '') or data.get('first_name', '')
        last_name = data.get('lastName', '') or data.get('last_name', '')
        full_name = data.get('name', '') or data.get('fullName', '') or f"{first_name} {last_name}".strip()
        
        profile_data = {
            'profile_url': profile_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'name': full_name or 'Unknown',
            'headline': data.get('headline', '') or data.get('title', ''),
            'location': data.get('location', '') or data.get('geo', ''),
            'about': data.get('summary', '') or data.get('about', ''),
            'experience': self._parse_experience(data.get('experience', []) or data.get('positions', [])),
            'education': self._parse_education(data.get('education', []) or data.get('schools', [])),
            'skills': data.get('skills', []),
            'raw_text': str(data)[:5000]
        }
        
        return profile_data
    
    def _parse_experience(self, experience_data: List[Dict]) -> List[Dict[str, str]]:
        """Parse experience data from RapidAPI format"""
        experience_list = []
        
        for exp in experience_data[:5]:  # Top 5 positions
            experience_list.append({
                'title': exp.get('title', ''),
                'company': exp.get('companyName', ''),
                'duration': f"{exp.get('timePeriod', {}).get('startDate', '')} - {exp.get('timePeriod', {}).get('endDate', 'Present')}",
                'description': exp.get('description', '')[:500]
            })
        
        return experience_list
    
    def _parse_education(self, education_data: List[Dict]) -> List[Dict[str, str]]:
        """Parse education data from RapidAPI format"""
        education_list = []
        
        for edu in education_data[:3]:  # Top 3 schools
            education_list.append({
                'school': edu.get('schoolName', ''),
                'degree': edu.get('degreeName', ''),
                'field': edu.get('fieldOfStudy', ''),
                'years': f"{edu.get('timePeriod', {}).get('startDate', '')} - {edu.get('timePeriod', {}).get('endDate', '')}"
            })
        
        return education_list
    
    def _extract_profile_urls_from_search(self, data: Dict) -> List[str]:
        """Extract profile URLs from search results"""
        profile_urls = []
        
        results = data.get('data', [])
        for result in results:
            profile_url = result.get('url', '') or result.get('profileUrl', '')
            if profile_url and 'linkedin.com/in/' in profile_url:
                profile_urls.append(profile_url)
        
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
def scrape_linkedin_profiles(profile_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape multiple LinkedIn profiles using RapidAPI
    
    Args:
        profile_urls: List of LinkedIn profile URLs
        
    Returns:
        List of profile data dictionaries
    """
    client = LinkedInRapidAPIClient()
    return client.scrape_multiple_profiles(profile_urls)


def search_linkedin_candidates(
    job_title: str,
    location: str,
    num_candidates: int = 10,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    open_to_work: bool = False
) -> List[str]:
    """
    Search LinkedIn for candidate profiles using RapidAPI
    
    Args:
        job_title: Job title or keywords
        location: Geographic location
        num_candidates: Number of candidates to find
        min_experience: Minimum years of experience (not used by RapidAPI)
        max_experience: Maximum years of experience (not used by RapidAPI)
        open_to_work: Filter for open to work candidates
        
    Returns:
        List of LinkedIn profile URLs
    """
    client = LinkedInRapidAPIClient()
    return client.search_linkedin_people(
        keywords=job_title,
        location=location,
        limit=num_candidates,
        open_to_work=open_to_work
    )


# Test function
if __name__ == "__main__":
    # Test with a public LinkedIn profile
    client = LinkedInRapidAPIClient()
    
    # Test search
    profiles = client.search_linkedin_people("Data Scientist", location="San Francisco", limit=5)
    print(f"Found {len(profiles)} profiles")
    
    # Test profile scraping if we found any
    if profiles:
        profile = client.scrape_linkedin_profile(profiles[0])
        print(f"Profile: {profile.get('name')}")
        print(f"Headline: {profile.get('headline')}")
