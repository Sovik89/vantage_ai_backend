"""
Mock LinkedIn Candidate Generator
Generates realistic fake LinkedIn profiles for testing and demo purposes
"""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uuid

# Mock data pools
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "William",
    "Mia", "James", "Charlotte", "Benjamin", "Amelia", "Lucas", "Harper", "Henry", "Evelyn", "Alexander",
    "Priya", "Raj", "Ananya", "Arjun", "Neha", "Rohan", "Diya", "Aditya", "Sara", "Vikram",
    "Maria", "Carlos", "Ana", "Diego", "Sofia", "Miguel", "Lucia", "Juan", "Isabella", "Pablo"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Patel", "Singh", "Kumar", "Shah", "Sharma", "Gupta", "Reddy", "Mehta", "Joshi", "Rao",
    "Lee", "Kim", "Park", "Chen", "Wang", "Zhang", "Liu", "Yang", "Wu", "Huang",
    "Anderson", "Taylor", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Moore"
]

LOCATIONS = [
    "San Francisco, CA", "San Jose, CA", "Palo Alto, CA", "Mountain View, CA", "Sunnyvale, CA",
    "New York, NY", "Seattle, WA", "Austin, TX", "Boston, MA", "Chicago, IL",
    "Los Angeles, CA", "Denver, CO", "Portland, OR", "Atlanta, GA", "Remote, United States",
    "Bangalore, India", "Hyderabad, India", "Mumbai, India", "Pune, India", "Delhi, India"
]

# Job titles by role
DATA_SCIENTIST_TITLES = [
    "Senior Data Scientist", "Lead Data Scientist", "Data Scientist", "Principal Data Scientist",
    "Machine Learning Engineer", "ML Engineer", "AI Research Scientist", "Applied Scientist",
    "Data Science Manager", "Staff Data Scientist"
]

DATA_ENGINEER_TITLES = [
    "Senior Data Engineer", "Lead Data Engineer", "Data Engineer", "Principal Data Engineer",
    "Staff Data Engineer", "Data Platform Engineer", "Big Data Engineer", "Analytics Engineer",
    "Data Infrastructure Engineer", "ETL Developer"
]

SOFTWARE_ENGINEER_TITLES = [
    "Senior Software Engineer", "Lead Software Engineer", "Software Engineer", "Principal Engineer",
    "Staff Software Engineer", "Backend Engineer", "Full Stack Engineer", "Frontend Engineer",
    "Software Development Engineer", "Solutions Architect"
]

HR_TITLES = [
    "Senior HR Manager", "HR Director", "HR Business Partner", "Talent Acquisition Manager",
    "People Operations Manager", "HRIS Manager", "HR Analytics Manager", "Compensation Manager",
    "Employee Relations Manager", "HR Generalist"
]

COMPANIES = [
    "Google", "Meta", "Amazon", "Microsoft", "Apple", "Netflix", "Tesla", "Uber", "Airbnb", "Stripe",
    "Salesforce", "Oracle", "Adobe", "IBM", "Intel", "NVIDIA", "Cisco", "VMware", "ServiceNow", "Databricks",
    "Snowflake", "MongoDB", "Confluent", "Atlassian", "Slack", "Zoom", "DocuSign", "Square", "PayPal", "eBay",
    "LinkedIn", "Twitter", "Reddit", "Pinterest", "Snap", "Lyft", "DoorDash", "Instacart", "Robinhood", "Coinbase"
]

SKILLS_BY_ROLE = {
    "data_scientist": [
        "Python", "R", "SQL", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn",
        "Pandas", "NumPy", "Statistics", "Data Visualization", "Tableau", "Power BI", "NLP", "Computer Vision",
        "A/B Testing", "Experimental Design", "Feature Engineering", "Model Deployment", "AWS", "GCP", "Azure"
    ],
    "data_engineer": [
        "Python", "SQL", "Apache Spark", "Hadoop", "Kafka", "Airflow", "ETL", "Data Warehousing",
        "Snowflake", "Redshift", "BigQuery", "Databricks", "AWS", "GCP", "Azure", "Docker", "Kubernetes",
        "Scala", "Java", "Data Modeling", "Data Pipeline", "DBT", "Terraform"
    ],
    "software_engineer": [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "Spring Boot", "Django", "Flask",
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "CI/CD", "Git", "SQL", "NoSQL", "REST APIs",
        "Microservices", "GraphQL", "Redis", "MongoDB"
    ],
    "hr": [
        "HRIS Systems", "Workday", "SAP SuccessFactors", "ADP", "Talent Management", "Recruiting",
        "Performance Management", "Compensation & Benefits", "Employee Relations", "HR Analytics",
        "Organizational Development", "Change Management", "Leadership Development", "Training & Development"
    ]
}

DEGREES = [
    "Bachelor of Science in Computer Science",
    "Master of Science in Data Science",
    "Master of Science in Computer Science",
    "Bachelor of Engineering in Information Technology",
    "Master of Business Administration (MBA)",
    "Bachelor of Science in Statistics",
    "Master of Science in Machine Learning",
    "PhD in Computer Science",
    "Bachelor of Technology in Computer Engineering",
    "Master of Science in Artificial Intelligence"
]

UNIVERSITIES = [
    "Stanford University", "MIT", "Carnegie Mellon University", "UC Berkeley", "Georgia Tech",
    "University of Washington", "Cornell University", "University of Michigan", "UT Austin",
    "Columbia University", "Harvard University", "Yale University", "Princeton University",
    "IIT Bombay", "IIT Delhi", "IIT Madras", "IIT Kanpur", "BITS Pilani", "NIT Trichy"
]


def generate_mock_profile(job_role: str = "data_scientist") -> Dict[str, Any]:
    """Generate a single mock LinkedIn profile"""
    
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    full_name = f"{first_name} {last_name}"
    
    # Generate username-style profile URL
    username = f"{first_name.lower()}{last_name.lower()}{random.randint(100, 999)}"
    profile_url = f"https://www.linkedin.com/in/{username}/"
    
    # Select appropriate title based on role
    if job_role == "data_scientist":
        titles = DATA_SCIENTIST_TITLES
        skills_pool = SKILLS_BY_ROLE["data_scientist"]
    elif job_role == "data_engineer":
        titles = DATA_ENGINEER_TITLES
        skills_pool = SKILLS_BY_ROLE["data_engineer"]
    elif job_role == "software_engineer":
        titles = SOFTWARE_ENGINEER_TITLES
        skills_pool = SKILLS_BY_ROLE["software_engineer"]
    elif job_role == "hr":
        titles = HR_TITLES
        skills_pool = SKILLS_BY_ROLE["hr"]
    else:
        titles = DATA_SCIENTIST_TITLES
        skills_pool = SKILLS_BY_ROLE["data_scientist"]
    
    current_title = random.choice(titles)
    current_company = random.choice(COMPANIES)
    location = random.choice(LOCATIONS)
    
    # Generate experience (2-4 positions)
    num_positions = random.randint(2, 4)
    experience = []
    total_years = 0
    
    for i in range(num_positions):
        years_at_company = random.randint(1, 4)
        total_years += years_at_company
        
        if i == 0:  # Current position
            title = current_title
            company = current_company
            start_date = (datetime.now() - timedelta(days=365 * years_at_company)).strftime("%Y-%m")
            end_date = "Present"
        else:
            title = random.choice(titles)
            company = random.choice([c for c in COMPANIES if c != current_company])
            end_year = datetime.now().year - sum([random.randint(1, 4) for _ in range(i)])
            start_date = f"{end_year - years_at_company}-{random.randint(1, 12):02d}"
            end_date = f"{end_year}-{random.randint(1, 12):02d}"
        
        exp = {
            "title": title,
            "company": company,
            "duration": f"{start_date} - {end_date}",
            "description": f"Working on {random.sample(skills_pool, 3)} at {company}"
        }
        experience.append(exp)
    
    # Generate education (1-2 degrees)
    num_degrees = random.randint(1, 2)
    education = []
    
    for i in range(num_degrees):
        degree = random.choice(DEGREES)
        school = random.choice(UNIVERSITIES)
        grad_year = datetime.now().year - total_years - random.randint(0, 2)
        
        edu = {
            "school": school,
            "degree": degree,
            "field": "Computer Science" if "Computer" in degree else "Data Science",
            "years": f"{grad_year - 4} - {grad_year}"
        }
        education.append(edu)
    
    # Generate skills (8-15 skills)
    num_skills = random.randint(8, 15)
    skills = random.sample(skills_pool, min(num_skills, len(skills_pool)))
    
    # Generate about section
    about = f"{current_title} with {total_years}+ years of experience in {', '.join(random.sample(skills_pool, 3))}. "
    about += f"Currently working at {current_company}. "
    about += f"Passionate about solving complex problems and building scalable solutions."
    
    # Create profile data
    profile = {
        'profile_url': profile_url,
        'scraped_at': datetime.utcnow().isoformat(),
        'name': full_name,
        'headline': f"{current_title} at {current_company}",
        'location': location,
        'about': about,
        'experience': experience,
        'education': education,
        'skills': skills,
        'raw_text': f"{full_name} {current_title} {location} {about}"
    }
    
    return profile


def generate_mock_candidates(
    job_role: str = "data_scientist",
    num_candidates: int = 10,
    location: str = None
) -> List[Dict[str, Any]]:
    """
    Generate multiple mock LinkedIn profiles
    
    Args:
        job_role: Type of role (data_scientist, data_engineer, software_engineer, hr)
        num_candidates: Number of profiles to generate
        location: Optional location filter
        
    Returns:
        List of mock profile dictionaries
    """
    profiles = []
    
    for _ in range(num_candidates):
        profile = generate_mock_profile(job_role)
        
        # Apply location filter if specified
        if location and location.lower() not in ["remote", "any"]:
            # Try to match location
            if any(loc_part.lower() in profile['location'].lower() for loc_part in location.split(',')):
                profiles.append(profile)
            elif len(profiles) < num_candidates:
                # Override location for some profiles
                profile['location'] = location
                profiles.append(profile)
        else:
            profiles.append(profile)
    
    return profiles


def mock_search_linkedin_candidates(
    job_title: str,
    location: str,
    num_candidates: int = 10,
    min_experience: int = None,
    max_experience: int = None,
    open_to_work: bool = False
) -> List[str]:
    """
    Mock version of search_linkedin_candidates
    Returns mock profile URLs
    """
    # Determine job role from title
    job_title_lower = job_title.lower()
    if "data scientist" in job_title_lower or "machine learning" in job_title_lower:
        job_role = "data_scientist"
    elif "data engineer" in job_title_lower:
        job_role = "data_engineer"
    elif "software" in job_title_lower or "engineer" in job_title_lower:
        job_role = "software_engineer"
    elif "hr" in job_title_lower or "people" in job_title_lower:
        job_role = "hr"
    else:
        job_role = "data_scientist"
    
    # Generate profiles
    profiles = generate_mock_candidates(job_role, num_candidates, location)
    
    # Return just the URLs
    return [p['profile_url'] for p in profiles]


def mock_scrape_linkedin_profiles(profile_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Mock version of scrape_linkedin_profiles
    Returns mock profile data for given URLs
    """
    profiles = []
    
    for url in profile_urls:
        # Determine role from URL or random
        job_role = random.choice(["data_scientist", "data_engineer", "software_engineer"])
        profile = generate_mock_profile(job_role)
        profile['profile_url'] = url  # Use the provided URL
        profiles.append(profile)
    
    return profiles


# Test function
if __name__ == "__main__":
    print("🧪 Testing Mock LinkedIn Profile Generator\n")
    
    # Test single profile generation
    print("1️⃣ Single Data Scientist Profile:")
    profile = generate_mock_profile("data_scientist")
    print(f"   Name: {profile['name']}")
    print(f"   Headline: {profile['headline']}")
    print(f"   Location: {profile['location']}")
    print(f"   Skills: {', '.join(profile['skills'][:5])}...")
    print(f"   Experience: {len(profile['experience'])} positions\n")
    
    # Test multiple candidates
    print("2️⃣ Multiple Data Engineer Candidates:")
    profiles = generate_mock_candidates("data_engineer", 5, "San Jose")
    for i, p in enumerate(profiles, 1):
        print(f"   {i}. {p['name']} - {p['headline']}")
    print()
    
    # Test mock search
    print("3️⃣ Mock LinkedIn Search:")
    urls = mock_search_linkedin_candidates("Data Scientist", "San Francisco", 5)
    print(f"   Found {len(urls)} profile URLs:")
    for url in urls[:3]:
        print(f"   - {url}")
    print()
    
    # Test mock scraping
    print("4️⃣ Mock Profile Scraping:")
    profiles = mock_scrape_linkedin_profiles(urls[:2])
    for p in profiles:
        print(f"   - {p['name']}: {len(p['skills'])} skills, {len(p['experience'])} positions")
