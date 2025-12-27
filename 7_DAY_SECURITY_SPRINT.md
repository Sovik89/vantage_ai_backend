# 🚀 Vantage.AI Security Implementation - 7-Day Sprint
## Complete Authentication & RBAC by Friday, December 20, 2025

**Start Date:** Saturday, December 14, 2025  
**End Date:** Friday, December 20, 2025  
**Status:** 🎯 READY TO START  
**Goal:** Production-ready authentication system in 7 days  

---

## 📊 Sprint Overview

```
Day 1 (Sat)  → Database + Test Data         [8 hours]
Day 2 (Sun)  → Security Config + Utils       [8 hours]
Day 3 (Mon)  → Auth Endpoints (Backend)      [8 hours]
Day 4 (Tue)  → RBAC + Middleware             [8 hours]
Day 5 (Wed)  → Frontend Auth Integration     [10 hours]
Day 6 (Thu)  → Update Existing Routes        [8 hours]
Day 7 (Fri)  → Testing + Deployment          [10 hours]
────────────────────────────────────────────────────────
TOTAL: 60 hours over 7 days
```

---

## 🎯 Daily Breakdown

### **DAY 1 - Saturday, December 14** [8 hours]
**Focus:** Database Schema + Test Data

#### Morning Session (4 hours)
**Task 1.1: Create 6 Security Tables in BigQuery** [2 hours]

```sql
-- Run these in order in BigQuery Console

-- 1. Users Table (15 min)
CREATE TABLE `vantage-ai-prod.hr_insights.users` (
    user_id STRING NOT NULL,
    email STRING NOT NULL,
    password_hash STRING NOT NULL,
    full_name STRING,
    phone STRING,
    user_type STRING NOT NULL,
    organization_id STRING,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verification_token STRING,
    email_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    last_login_ip STRING,
    login_attempts INT64 DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY email, user_type, organization_id;

-- 2. Organizations Table (15 min)
CREATE TABLE `vantage-ai-prod.hr_insights.organizations` (
    organization_id STRING NOT NULL,
    organization_name STRING NOT NULL,
    organization_type STRING,
    owner_user_id STRING NOT NULL,
    subscription_plan STRING NOT NULL,
    subscription_status STRING NOT NULL,
    subscription_start_date TIMESTAMP,
    subscription_end_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    billing_email STRING,
    max_users INT64 DEFAULT 5,
    current_users INT64 DEFAULT 0,
    max_storage_gb INT64 DEFAULT 10,
    max_monthly_jobs INT64 DEFAULT 100,
    current_monthly_jobs INT64 DEFAULT 0,
    jobs_reset_date DATE,
    api_key STRING,
    api_calls_limit INT64,
    api_calls_used INT64 DEFAULT 0,
    api_calls_reset_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY subscription_plan, subscription_status;

-- 3. Roles Table (15 min)
CREATE TABLE `vantage-ai-prod.hr_insights.roles` (
    role_id STRING NOT NULL,
    role_name STRING NOT NULL,
    description STRING,
    can_access_linkedin BOOLEAN DEFAULT FALSE,
    can_access_ats BOOLEAN DEFAULT FALSE,
    can_access_journal BOOLEAN DEFAULT FALSE,
    can_access_sentiment BOOLEAN DEFAULT FALSE,
    can_access_dashboard BOOLEAN DEFAULT FALSE,
    can_access_analytics BOOLEAN DEFAULT FALSE,
    can_create BOOLEAN DEFAULT TRUE,
    can_read BOOLEAN DEFAULT TRUE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_export BOOLEAN DEFAULT FALSE,
    can_manage_users BOOLEAN DEFAULT FALSE,
    can_manage_billing BOOLEAN DEFAULT FALSE,
    can_view_audit_logs BOOLEAN DEFAULT FALSE,
    can_manage_organizations BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Insert 5 predefined roles
INSERT INTO `vantage-ai-prod.hr_insights.roles` VALUES
('role_owner', 'Platform Owner', 'Fiinch.ai admin', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, CURRENT_TIMESTAMP()),
('role_freelancer', 'Freelancer', 'Limited access', TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, CURRENT_TIMESTAMP()),
('role_basic', 'Basic Plan', 'Organization basic', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, CURRENT_TIMESTAMP()),
('role_gold', 'Gold Plan', 'Organization gold', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, CURRENT_TIMESTAMP()),
('role_premium', 'Premium Plan', 'Organization premium', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, CURRENT_TIMESTAMP());

-- 4. User Roles Table (10 min)
CREATE TABLE `vantage-ai-prod.hr_insights.user_roles` (
    user_role_id STRING NOT NULL,
    user_id STRING NOT NULL,
    role_id STRING NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    assigned_by STRING,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
)
PARTITION BY DATE(assigned_at)
CLUSTER BY user_id, role_id;

-- 5. User Sessions Table (10 min)
CREATE TABLE `vantage-ai-prod.hr_insights.user_sessions` (
    session_id STRING NOT NULL,
    user_id STRING NOT NULL,
    token_hash STRING NOT NULL,
    refresh_token_hash STRING,
    ip_address STRING,
    user_agent STRING,
    device_type STRING,
    expires_at TIMESTAMP NOT NULL,
    last_activity_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    logout_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, is_active, expires_at;

-- 6. Audit Logs Table (10 min)
CREATE TABLE `vantage-ai-prod.hr_insights.audit_logs` (
    log_id STRING NOT NULL,
    user_id STRING,
    organization_id STRING,
    action STRING NOT NULL,
    resource_type STRING,
    resource_id STRING,
    ip_address STRING,
    user_agent STRING,
    request_method STRING,
    request_path STRING,
    status STRING,
    error_message STRING,
    response_code INT64,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, action, status;
```

**Verification Query:**
```sql
SELECT 
    table_id,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), creation_time, MINUTE) as created_mins_ago,
    row_count
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id IN ('users', 'organizations', 'roles', 'user_roles', 'user_sessions', 'audit_logs')
ORDER BY table_id;
```

**Expected Output:** 6 tables, roles table should have 5 rows

**Task 1.2: Create Test Data** [1 hour]

```sql
-- Owner account for Fiinch.ai
INSERT INTO `vantage-ai-prod.hr_insights.users` VALUES (
    GENERATE_UUID(),
    'admin@fiinch.ai',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', -- Password: Admin@123
    'Fiinch Admin',
    '+1234567890',
    'owner',
    NULL,
    TRUE,
    TRUE,
    NULL,
    CURRENT_TIMESTAMP(),
    NULL,
    NULL,
    0,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    'system'
);

-- Test freelancer
INSERT INTO `vantage-ai-prod.hr_insights.users` VALUES (
    GENERATE_UUID(),
    'freelancer@test.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', -- Password: Test@123
    'Test Freelancer',
    NULL,
    'freelancer',
    NULL,
    TRUE,
    TRUE,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    'system'
);

-- Test organization user
INSERT INTO `vantage-ai-prod.hr_insights.users` VALUES (
    GENERATE_UUID(),
    'org@test.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', -- Password: Test@123
    'Test Organization User',
    NULL,
    'organization',
    (SELECT GENERATE_UUID()), -- Will create org after
    TRUE,
    TRUE,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    'system'
);

-- Create test organization
INSERT INTO `vantage-ai-prod.hr_insights.organizations` VALUES (
    (SELECT organization_id FROM `vantage-ai-prod.hr_insights.users` WHERE email = 'org@test.com'),
    'Test Company Inc',
    'startup',
    (SELECT user_id FROM `vantage-ai-prod.hr_insights.users` WHERE email = 'org@test.com'),
    'gold',
    'trial',
    CURRENT_TIMESTAMP(),
    TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY),
    TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 14 DAY),
    'billing@test.com',
    20,
    1,
    50,
    500,
    0,
    CURRENT_DATE(),
    CONCAT('vantage_', GENERATE_UUID()),
    NULL,
    0,
    NULL,
    TRUE,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP()
);

-- Assign roles
INSERT INTO `vantage-ai-prod.hr_insights.user_roles` 
SELECT 
    GENERATE_UUID(),
    u.user_id,
    CASE 
        WHEN u.user_type = 'owner' THEN 'role_owner'
        WHEN u.user_type = 'freelancer' THEN 'role_freelancer'
        WHEN u.user_type = 'organization' THEN 'role_gold'
    END,
    CURRENT_TIMESTAMP(),
    'system',
    NULL,
    TRUE
FROM `vantage-ai-prod.hr_insights.users` u;

-- Verify test data
SELECT 
    u.email,
    u.user_type,
    r.role_name,
    o.organization_name,
    o.subscription_plan
FROM `vantage-ai-prod.hr_insights.users` u
JOIN `vantage-ai-prod.hr_insights.user_roles` ur ON u.user_id = ur.user_id
JOIN `vantage-ai-prod.hr_insights.roles` r ON ur.role_id = r.role_id
LEFT JOIN `vantage-ai-prod.hr_insights.organizations` o ON u.organization_id = o.organization_id;
```

**Expected Output:** 3 users with proper roles

**Task 1.3: Create Helper Queries** [1 hour]

Create file: `vantage_api/sql/helper_queries.sql`

```sql
-- Get user with permissions
CREATE TEMP FUNCTION get_user_permissions(p_user_id STRING) AS ((
    SELECT ARRAY_AGG(STRUCT(
        r.can_access_linkedin,
        r.can_access_ats,
        r.can_access_journal,
        r.can_access_sentiment,
        r.can_access_dashboard,
        r.can_create,
        r.can_read,
        r.can_update,
        r.can_delete,
        r.can_export
    ))
    FROM `vantage-ai-prod.hr_insights.user_roles` ur
    JOIN `vantage-ai-prod.hr_insights.roles` r ON ur.role_id = r.role_id
    WHERE ur.user_id = p_user_id AND ur.is_active = TRUE
));

-- Check if email exists
SELECT EXISTS(
    SELECT 1 FROM `vantage-ai-prod.hr_insights.users`
    WHERE email = @email
) as email_exists;

-- Get user by email
SELECT * FROM `vantage-ai-prod.hr_insights.users`
WHERE email = @email AND is_active = TRUE;

-- Increment login attempts
UPDATE `vantage-ai-prod.hr_insights.users`
SET login_attempts = login_attempts + 1,
    locked_until = CASE 
        WHEN login_attempts + 1 >= 5 THEN TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE)
        ELSE locked_until
    END
WHERE user_id = @user_id;

-- Reset login attempts on success
UPDATE `vantage-ai-prod.hr_insights.users`
SET login_attempts = 0,
    locked_until = NULL,
    last_login_at = CURRENT_TIMESTAMP(),
    last_login_ip = @ip_address
WHERE user_id = @user_id;

-- Clean expired sessions (run daily)
DELETE FROM `vantage-ai-prod.hr_insights.user_sessions`
WHERE expires_at < CURRENT_TIMESTAMP()
  AND is_active = FALSE;

-- Get active sessions for user
SELECT 
    session_id,
    ip_address,
    device_type,
    created_at,
    last_activity_at,
    expires_at
FROM `vantage-ai-prod.hr_insights.user_sessions`
WHERE user_id = @user_id 
  AND is_active = TRUE
  AND expires_at > CURRENT_TIMESTAMP()
ORDER BY last_activity_at DESC;
```

#### Afternoon Session (4 hours)

**Task 1.4: Install Security Dependencies** [30 min]

```powershell
# Navigate to project
cd c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_api

# Activate virtual environment
.\pa_env\Scripts\Activate.ps1

# Install new dependencies
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install email-validator==2.1.0
pip install slowapi==0.1.9

# Verify installations
pip list | Select-String "jose|passlib|email|slowapi"

# Update requirements.txt
pip freeze > requirements.txt
```

**Task 1.5: Create Project Structure** [30 min]

```powershell
# Create new directories
New-Item -ItemType Directory -Path "vantage_api/middleware" -Force
New-Item -ItemType Directory -Path "vantage_api/sql" -Force

# Create placeholder files
New-Item -ItemType File -Path "vantage_api/middleware/__init__.py"
New-Item -ItemType File -Path "vantage_api/security_config.py"
New-Item -ItemType File -Path "vantage_api/utils/auth_utils.py"
New-Item -ItemType File -Path "vantage_api/utils/rbac_utils.py"
New-Item -ItemType File -Path "vantage_api/schemas/auth_models.py"
New-Item -ItemType File -Path "vantage_api/routers/auth.py"
New-Item -ItemType File -Path "vantage_api/routers/users.py"
New-Item -ItemType File -Path "vantage_api/middleware/auth_middleware.py"
New-Item -ItemType File -Path "vantage_api/middleware/rate_limiter.py"

# Verify structure
Get-ChildItem -Recurse -File | Where-Object { $_.Name -match "auth|security" } | Select-Object FullName
```

**Task 1.6: Set Environment Variables** [30 min]

Create `.env` file in `vantage_api/`:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-minimum-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
BCRYPT_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=5

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Email (for future email verification)
EMAIL_FROM=noreply@vantage.ai
```

Load in PowerShell:
```powershell
# Read .env and set environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

# Verify
$env:JWT_SECRET_KEY
```

**Task 1.7: Test BigQuery Connection** [2 hours]

Create test file: `vantage_api/test_security_db.py`

```python
"""Test security database tables"""
from google.cloud import bigquery
import config

def test_tables_exist():
    """Test that all security tables exist"""
    client = bigquery.Client(project=config.PROJECT_ID)
    
    required_tables = ['users', 'organizations', 'roles', 'user_roles', 'user_sessions', 'audit_logs']
    
    query = f"""
    SELECT table_id
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.__TABLES__`
    WHERE table_id IN UNNEST(@table_list)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("table_list", "STRING", required_tables)
        ]
    )
    
    results = list(client.query(query, job_config=job_config).result())
    found_tables = [row.table_id for row in results]
    
    print(f"✓ Found {len(found_tables)}/{len(required_tables)} tables:")
    for table in found_tables:
        print(f"  - {table}")
    
    missing = set(required_tables) - set(found_tables)
    if missing:
        print(f"✗ Missing tables: {missing}")
        return False
    
    return True

def test_roles_populated():
    """Test that roles table has 5 predefined roles"""
    client = bigquery.Client(project=config.PROJECT_ID)
    
    query = f"""
    SELECT role_id, role_name
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.roles`
    ORDER BY role_id
    """
    
    results = list(client.query(query).result())
    
    print(f"\n✓ Found {len(results)} roles:")
    for row in results:
        print(f"  - {row.role_id}: {row.role_name}")
    
    expected_roles = ['role_owner', 'role_freelancer', 'role_basic', 'role_gold', 'role_premium']
    found_roles = [row.role_id for row in results]
    
    if set(expected_roles) == set(found_roles):
        print("✓ All expected roles present")
        return True
    else:
        print(f"✗ Missing roles: {set(expected_roles) - set(found_roles)}")
        return False

def test_users_exist():
    """Test that test users exist"""
    client = bigquery.Client(project=config.PROJECT_ID)
    
    query = f"""
    SELECT 
        u.email,
        u.user_type,
        r.role_name
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.users` u
    JOIN `{config.PROJECT_ID}.{config.BQ_DATASET}.user_roles` ur ON u.user_id = ur.user_id
    JOIN `{config.PROJECT_ID}.{config.BQ_DATASET}.roles` r ON ur.role_id = r.role_id
    WHERE ur.is_active = TRUE
    """
    
    results = list(client.query(query).result())
    
    print(f"\n✓ Found {len(results)} test users:")
    for row in results:
        print(f"  - {row.email} ({row.user_type}) -> {row.role_name}")
    
    return len(results) >= 3

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Security Database Setup")
    print("=" * 60)
    
    success = True
    
    print("\n1. Testing table existence...")
    success = test_tables_exist() and success
    
    print("\n2. Testing roles...")
    success = test_roles_populated() and success
    
    print("\n3. Testing users...")
    success = test_users_exist() and success
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Database setup complete!")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
    print("=" * 60)
```

Run test:
```powershell
python test_security_db.py
```

**✅ Day 1 Complete Checklist:**
- [ ] 6 BigQuery tables created
- [ ] 5 roles inserted
- [ ] 3 test users created
- [ ] Dependencies installed
- [ ] Project structure created
- [ ] Environment variables set
- [ ] Database tests passing

---

### **DAY 2 - Sunday, December 15** [8 hours]
**Focus:** Security Configuration + Authentication Utilities

#### Morning Session (4 hours)

**Task 2.1: Create `security_config.py`** [1 hour]

```python
"""Security Configuration"""
import os
from datetime import timedelta

# JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
BCRYPT_ROUNDS = 12
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}|;:,.<>?"

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_AUTH_PER_MINUTE = 5

# Session
MAX_SESSIONS_PER_USER = 5
SESSION_INACTIVITY_TIMEOUT = timedelta(hours=24)

# Account Security
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
EMAIL_VERIFICATION_REQUIRED = False  # Set to True when email service ready

# API Key
API_KEY_PREFIX = "vantage_"
API_KEY_LENGTH = 32

# CORS
CORS_ALLOW_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

def validate_config():
    """Validate security config"""
    if len(SECRET_KEY) < 32 or "CHANGE" in SECRET_KEY:
        print("⚠️  WARNING: JWT_SECRET_KEY should be changed in production!")

validate_config()
```

**Task 2.2: Create `utils/auth_utils.py`** [2 hours]

```python
"""Authentication Utilities"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid
import secrets
import hashlib
import security_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password"""
    try:
        return pwd_context.verify(plain, hashed)
    except:
        return False

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password meets requirements"""
    if len(password) < security_config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {security_config.PASSWORD_MIN_LENGTH} characters"
    
    if security_config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain uppercase letter"
    
    if security_config.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain lowercase letter"
    
    if security_config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain digit"
    
    if security_config.PASSWORD_REQUIRE_SPECIAL:
        if not any(c in security_config.PASSWORD_SPECIAL_CHARS for c in password):
            return False, f"Password must contain special character"
    
    return True, "Valid"

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=security_config.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, security_config.SECRET_KEY, algorithm=security_config.ALGORITHM)

def create_refresh_token(data: Dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=security_config.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, security_config.SECRET_KEY, algorithm=security_config.ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
    """Verify and decode JWT"""
    try:
        payload = jwt.decode(token, security_config.SECRET_KEY, algorithms=[security_config.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None

def hash_token(token: str) -> str:
    """SHA256 hash of token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate API key"""
    return f"{security_config.API_KEY_PREFIX}{secrets.token_urlsafe(security_config.API_KEY_LENGTH)}"

def generate_verification_token() -> str:
    """Generate email verification token"""
    return secrets.token_urlsafe(32)
```

**Task 2.3: Create `utils/rbac_utils.py`** [1 hour]

```python
"""Role-Based Access Control Utilities"""
from typing import Dict
from google.cloud import bigquery
import config

def get_bigquery_client():
    """Get BigQuery client"""
    return bigquery.Client(project=config.PROJECT_ID)

def get_user_permissions(user_id: str) -> Dict:
    """Get aggregated permissions for user"""
    client = get_bigquery_client()
    
    query = f"""
    SELECT 
        MAX(CAST(r.can_access_linkedin AS INT64)) as can_access_linkedin,
        MAX(CAST(r.can_access_ats AS INT64)) as can_access_ats,
        MAX(CAST(r.can_access_journal AS INT64)) as can_access_journal,
        MAX(CAST(r.can_access_sentiment AS INT64)) as can_access_sentiment,
        MAX(CAST(r.can_access_dashboard AS INT64)) as can_access_dashboard,
        MAX(CAST(r.can_access_analytics AS INT64)) as can_access_analytics,
        MAX(CAST(r.can_create AS INT64)) as can_create,
        MAX(CAST(r.can_read AS INT64)) as can_read,
        MAX(CAST(r.can_update AS INT64)) as can_update,
        MAX(CAST(r.can_delete AS INT64)) as can_delete,
        MAX(CAST(r.can_export AS INT64)) as can_export,
        MAX(CAST(r.can_manage_users AS INT64)) as can_manage_users,
        MAX(CAST(r.can_manage_billing AS INT64)) as can_manage_billing,
        MAX(CAST(r.can_view_audit_logs AS INT64)) as can_view_audit_logs,
        MAX(CAST(r.can_manage_organizations AS INT64)) as can_manage_organizations
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.user_roles` ur
    JOIN `{config.PROJECT_ID}.{config.BQ_DATASET}.roles` r ON ur.role_id = r.role_id
    WHERE ur.user_id = @user_id AND ur.is_active = TRUE
    GROUP BY ur.user_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    
    results = list(client.query(query, job_config=job_config).result())
    
    if not results:
        # Return all False if no permissions found
        return {
            'can_access_linkedin': False,
            'can_access_ats': False,
            'can_access_journal': False,
            'can_access_sentiment': False,
            'can_access_dashboard': False,
            'can_access_analytics': False,
            'can_create': False,
            'can_read': False,
            'can_update': False,
            'can_delete': False,
            'can_export': False,
            'can_manage_users': False,
            'can_manage_billing': False,
            'can_view_audit_logs': False,
            'can_manage_organizations': False,
        }
    
    row = results[0]
    return {
        'can_access_linkedin': bool(row.can_access_linkedin),
        'can_access_ats': bool(row.can_access_ats),
        'can_access_journal': bool(row.can_access_journal),
        'can_access_sentiment': bool(row.can_access_sentiment),
        'can_access_dashboard': bool(row.can_access_dashboard),
        'can_access_analytics': bool(row.can_access_analytics),
        'can_create': bool(row.can_create),
        'can_read': bool(row.can_read),
        'can_update': bool(row.can_update),
        'can_delete': bool(row.can_delete),
        'can_export': bool(row.can_export),
        'can_manage_users': bool(row.can_manage_users),
        'can_manage_billing': bool(row.can_manage_billing),
        'can_view_audit_logs': bool(row.can_view_audit_logs),
        'can_manage_organizations': bool(row.can_manage_organizations),
    }

def check_feature_access(user_id: str, feature: str) -> bool:
    """Check if user can access feature"""
    permissions = get_user_permissions(user_id)
    feature_map = {
        'linkedin': 'can_access_linkedin',
        'ats': 'can_access_ats',
        'journal': 'can_access_journal',
        'sentiment': 'can_access_sentiment',
        'dashboard': 'can_access_dashboard',
        'analytics': 'can_access_analytics',
    }
    perm_key = feature_map.get(feature.lower())
    return permissions.get(perm_key, False) if perm_key else False
```

#### Afternoon Session (4 hours)

**Task 2.4: Create Test Suite for Utils** [2 hours]

Create: `vantage_api/test_auth_utils.py`

```python
"""Test authentication utilities"""
from utils import auth_utils
import security_config

def test_password_hashing():
    """Test password hashing and verification"""
    print("\n1. Testing password hashing...")
    password = "Test@123"
    
    # Hash password
    hashed = auth_utils.hash_password(password)
    print(f"   Original: {password}")
    print(f"   Hashed: {hashed[:50]}...")
    
    # Verify correct password
    assert auth_utils.verify_password(password, hashed), "✗ Correct password failed"
    print("   ✓ Correct password verified")
    
    # Verify wrong password
    assert not auth_utils.verify_password("WrongPass", hashed), "✗ Wrong password accepted"
    print("   ✓ Wrong password rejected")

def test_password_validation():
    """Test password strength validation"""
    print("\n2. Testing password validation...")
    
    test_cases = [
        ("Test@123", True, "Valid password"),
        ("short", False, "Too short"),
        ("alllowercase123!", False, "No uppercase"),
        ("ALLUPPERCASE123!", False, "No lowercase"),
        ("NoDigitsHere!", False, "No digits"),
        ("NoSpecial123", False, "No special char"),
    ]
    
    for password, should_pass, description in test_cases:
        is_valid, msg = auth_utils.validate_password_strength(password)
        expected = "✓" if should_pass else "✗"
        actual = "✓" if is_valid else "✗"
        status = "PASS" if (is_valid == should_pass) else "FAIL"
        print(f"   [{status}] {password:20s} -> {actual} {description}")
        assert is_valid == should_pass, f"Password validation failed for: {password}"

def test_jwt_tokens():
    """Test JWT token creation and verification"""
    print("\n3. Testing JWT tokens...")
    
    # Create access token
    data = {"sub": "user-123", "email": "test@example.com"}
    access_token = auth_utils.create_access_token(data)
    print(f"   Access token created: {access_token[:50]}...")
    
    # Verify access token
    payload = auth_utils.verify_token(access_token, "access")
    assert payload is not None, "✗ Token verification failed"
    assert payload["sub"] == "user-123", "✗ Token payload mismatch"
    print(f"   ✓ Access token verified: {payload['sub']}")
    
    # Create refresh token
    refresh_token = auth_utils.create_refresh_token(data)
    print(f"   Refresh token created: {refresh_token[:50]}...")
    
    # Verify refresh token
    payload = auth_utils.verify_token(refresh_token, "refresh")
    assert payload is not None, "✗ Refresh token verification failed"
    print(f"   ✓ Refresh token verified: {payload['sub']}")
    
    # Test wrong token type
    payload = auth_utils.verify_token(access_token, "refresh")
    assert payload is None, "✗ Wrong token type accepted"
    print("   ✓ Wrong token type rejected")

def test_api_key_generation():
    """Test API key generation"""
    print("\n4. Testing API key generation...")
    
    api_key = auth_utils.generate_api_key()
    print(f"   Generated API key: {api_key}")
    
    assert api_key.startswith(security_config.API_KEY_PREFIX), "✗ Wrong prefix"
    assert len(api_key) > 40, "✗ Too short"
    print("   ✓ API key format valid")

def test_rbac():
    """Test RBAC utilities"""
    print("\n5. Testing RBAC...")
    
    # Get permissions for test user (admin@fiinch.ai)
    from utils import rbac_utils
    from google.cloud import bigquery
    import config
    
    client = bigquery.Client(project=config.PROJECT_ID)
    query = f"SELECT user_id FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.users` WHERE email = 'admin@fiinch.ai'"
    results = list(client.query(query).result())
    
    if results:
        user_id = results[0].user_id
        permissions = rbac_utils.get_user_permissions(user_id)
        
        print(f"   User: admin@fiinch.ai")
        print(f"   Permissions: {sum(permissions.values())} of {len(permissions)} enabled")
        
        # Owner should have all permissions
        assert permissions['can_access_linkedin'], "✗ Missing LinkedIn access"
        assert permissions['can_manage_organizations'], "✗ Missing admin rights"
        print("   ✓ Owner permissions correct")
    else:
        print("   ⚠️  Test user not found - skipping RBAC test")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Authentication Utilities")
    print("=" * 60)
    
    try:
        test_password_hashing()
        test_password_validation()
        test_jwt_tokens()
        test_api_key_generation()
        test_rbac()
        
        print("\n" + "=" * 60)
        print("✅ ALL AUTHENTICATION TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
```

Run tests:
```powershell
python test_auth_utils.py
```

**Task 2.5: Create Pydantic Schemas** [2 hours]

Create: `vantage_api/schemas/auth_models.py`

```python
"""Authentication Pydantic Models"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class UserType(str, Enum):
    OWNER = "owner"
    FREELANCER = "freelancer"
    ORGANIZATION = "organization"

class SubscriptionPlan(str, Enum):
    BASIC = "basic"
    GOLD = "gold"
    PREMIUM = "premium"

# REQUEST MODELS
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    user_type: UserType
    organization_name: Optional[str] = None
    organization_type: Optional[str] = None
    
    @validator('organization_name')
    def validate_org(cls, v, values):
        if values.get('user_type') == UserType.ORGANIZATION and not v:
            raise ValueError('organization_name required for organization users')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# RESPONSE MODELS
class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: str
    user_type: UserType
    organization_id: Optional[str] = None
    is_verified: bool = False

class OrganizationInfo(BaseModel):
    organization_id: str
    organization_name: str
    subscription_plan: SubscriptionPlan
    subscription_status: str
    max_users: int
    current_users: int

class Permissions(BaseModel):
    can_access_linkedin: bool = False
    can_access_ats: bool = False
    can_access_journal: bool = False
    can_access_sentiment: bool = False
    can_access_dashboard: bool = False
    can_access_analytics: bool = False
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_export: bool = False
    can_manage_users: bool = False
    can_manage_billing: bool = False
    can_view_audit_logs: bool = False
    can_manage_organizations: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
    organization: Optional[OrganizationInfo] = None
    permissions: Permissions

class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    user_type: UserType
    is_active: bool
    is_verified: bool
    message: str = "Registration successful"

class MessageResponse(BaseModel):
    message: str
    success: bool = True
```

**✅ Day 2 Complete Checklist:**
- [ ] `security_config.py` created
- [ ] `utils/auth_utils.py` created (password, JWT, API keys)
- [ ] `utils/rbac_utils.py` created (permissions)
- [ ] `schemas/auth_models.py` created
- [ ] All utility tests passing
- [ ] JWT tokens generating correctly

---

### **DAY 3 - Monday, December 16** [8 hours]
**Focus:** Authentication Endpoints (Register, Login, Logout, Refresh)

*[Continues with detailed Day 3-7 implementation...]*

---

## 📊 Progress Tracker

**Use this table daily:**

| Day | Date | Tasks | Status | Hours | Blockers |
|-----|------|-------|--------|-------|----------|
| 1 | Dec 14 | Database + Test Data | ⬜ | 0/8 | |
| 2 | Dec 15 | Config + Utils | ⬜ | 0/8 | |
| 3 | Dec 16 | Auth Endpoints | ⬜ | 0/8 | |
| 4 | Dec 17 | RBAC + Middleware | ⬜ | 0/8 | |
| 5 | Dec 18 | Frontend Auth | ⬜ | 0/10 | |
| 6 | Dec 19 | Update Routes | ⬜ | 0/8 | |
| 7 | Dec 20 | Testing + Deploy | ⬜ | 0/10 | |

---

## 🎯 Success Criteria

**By Friday, December 20 at 5 PM:**

✅ **Backend:**
- [ ] 6 BigQuery tables operational
- [ ] Register/Login/Logout endpoints working
- [ ] JWT authentication functional
- [ ] RBAC enforced on all routes
- [ ] Rate limiting active
- [ ] Audit logging enabled

✅ **Frontend:**
- [ ] Login/Register pages functional
- [ ] AuthContext providing user state
- [ ] Protected routes working
- [ ] Navbar showing user info
- [ ] Logout working

✅ **Testing:**
- [ ] Can register new users
- [ ] Can login with correct credentials
- [ ] Wrong password rejected
- [ ] Freelancer blocked from sentiment
- [ ] Organization user has full access
- [ ] Owner has admin access

✅ **Documentation:**
- [ ] API documentation updated
- [ ] User guide written
- [ ] Deployment notes created

---

## 🚨 Risk Mitigation

**Potential Blockers & Solutions:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| BigQuery table creation fails | Low | High | Have backup SQL scripts ready |
| JWT library issues | Low | Medium | Test on Day 2, fallback to alternative |
| Frontend integration delays | Medium | High | Start early (Day 5), allocate extra time |
| Test data issues | Medium | Low | Keep SQL scripts handy to recreate |
| Rate limiter conflicts | Low | Medium | Test thoroughly on Day 4 |

---

## 📞 Daily Standup Template

**Use this format daily:**

```
Date: [Date]
Day: [1-7]

COMPLETED YESTERDAY:
- [ ] Task 1
- [ ] Task 2

TODAY'S GOALS:
- [ ] Task 1
- [ ] Task 2

BLOCKERS:
- None / [Describe blocker]

HOURS WORKED: [X/8]
ON TRACK: Yes/No
```

---

## 🎉 Celebration Milestones

- **Day 1 Complete:** 🎯 Database foundation solid!
- **Day 3 Complete:** 🔐 Authentication working!
- **Day 5 Complete:** 🎨 Frontend integrated!
- **Day 7 Complete:** 🚀 **PRODUCTION READY!**

---

**LET'S BUILD THIS! START TOMORROW (SAT DEC 14) AT 9 AM** 💪
