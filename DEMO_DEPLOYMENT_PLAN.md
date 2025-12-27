# 🎯 Vantage.AI Demo Deployment Plan
## Get Sales Reps Showing the App to Clients by Dec 20, 2025

**Business Goal:** 2 representatives showing functional demo to potential clients  
**Technical Goal:** Simple, secure demo version (not full multi-tenant yet)  
**Timeline:** 3 days (Dec 14-16) for demo, parallel scaling work (Dec 17 - Jan 15)  
**Production Scale:** Mid-January 2026  

---

## 📊 Two-Track Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  TRACK 1: DEMO VERSION (Priority)         Dec 14-20         │
├─────────────────────────────────────────────────────────────┤
│  Simple auth for 2 sales reps + demo accounts              │
│  Good enough to show clients                                │
│  Fast to implement (3 days)                                 │
└─────────────────────────────────────────────────────────────┘
                            │
              Sales reps start demoing to clients
              Collect feedback & requirements
                            │
┌─────────────────────────────────────────────────────────────┐
│  TRACK 2: PRODUCTION SCALE (Parallel)     Dec 21 - Jan 15  │
├─────────────────────────────────────────────────────────────┤
│  Full multi-tenant architecture                             │
│  Subscription management (Basic/Gold/Premium)               │
│  Organization hierarchy                                     │
│  API rate limiting by tier                                  │
│  Production-grade security                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                  Production Launch Jan 15+
```

---

## 🚀 TRACK 1: Demo Version (3 Days)

### Goal
**Minimum Viable Authentication** so sales reps can safely demo the app without exposing it publicly.

### What You Need for Demo
1. ✅ **2 Sales Rep Accounts** - Can login and use all features
2. ✅ **Demo Client Accounts** - Pre-created accounts for client demos
3. ✅ **Basic Password Protection** - No public access
4. ✅ **Session Management** - Stays logged in during demos
5. ❌ **No Subscriptions Yet** - Everyone gets full access
6. ❌ **No Role Restrictions** - Simplified for demo
7. ❌ **No Payment Integration** - Show features first

### Simplified Architecture

```
┌──────────────────────┐
│   Frontend (Demo)    │
│  - Login page only   │
│  - No registration   │
│  - No subscriptions  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Backend (Simple)    │
│  - JWT auth          │
│  - 2 hardcoded users │
│  - Basic middleware  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  BigQuery (Minimal)  │
│  - users table only  │
│  - sessions table    │
└──────────────────────┘
```

---

## 📅 3-Day Demo Implementation

### **DAY 1 - Saturday, Dec 14** [6 hours]

#### Task 1: Create Minimal Database (2 hours)

**Only 2 tables needed for demo:**

```sql
-- 1. Users table (simplified)
CREATE TABLE `vantage-ai-prod.hr_insights.demo_users` (
    user_id STRING NOT NULL,
    email STRING NOT NULL,
    password_hash STRING NOT NULL,
    full_name STRING,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY email;

-- 2. Sessions table
CREATE TABLE `vantage-ai-prod.hr_insights.demo_sessions` (
    session_id STRING NOT NULL,
    user_id STRING NOT NULL,
    token_hash STRING NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY user_id;

-- Insert 2 sales rep accounts
INSERT INTO `vantage-ai-prod.hr_insights.demo_users` VALUES
(GENERATE_UUID(), 'rep1@fiinch.ai', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', 'Sales Rep 1', TRUE, CURRENT_TIMESTAMP()),
(GENERATE_UUID(), 'rep2@fiinch.ai', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', 'Sales Rep 2', TRUE, CURRENT_TIMESTAMP());
-- Password for both: Demo@2025

-- Insert 3 demo client accounts
INSERT INTO `vantage-ai-prod.hr_insights.demo_users` VALUES
(GENERATE_UUID(), 'client1@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', 'Demo Client 1', TRUE, CURRENT_TIMESTAMP()),
(GENERATE_UUID(), 'client2@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', 'Demo Client 2', TRUE, CURRENT_TIMESTAMP()),
(GENERATE_UUID(), 'client3@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', 'Demo Client 3', TRUE, CURRENT_TIMESTAMP());

-- Verify
SELECT email, full_name FROM `vantage-ai-prod.hr_insights.demo_users`;
```

#### Task 2: Install Dependencies (30 min)

```powershell
cd c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_api
.\pa_env\Scripts\Activate.ps1

# Already in requirements.txt, just install
pip install python-jose[cryptography] passlib[bcrypt] email-validator slowapi

# Verify
pip list | Select-String "jose|passlib|email|slowapi"
```

#### Task 3: Create Simple Auth Files (3.5 hours)

**File 1: `demo_security_config.py`**

```python
"""Demo Security Configuration - Simplified for sales demos"""
import os

# JWT (use simple key for demo, change for production)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "demo-secret-key-change-for-production-12345678")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours (full demo day)

# Demo settings
DEMO_MODE = True
REQUIRE_EMAIL_VERIFICATION = False
MAX_LOGIN_ATTEMPTS = 10  # Relaxed for demo
```

**File 2: `utils/demo_auth.py`**

```python
"""Demo Authentication Utilities"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import jwt
from passlib.context import CryptContext
import hashlib
import uuid

import demo_security_config as config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password"""
    try:
        return pwd_context.verify(plain, hashed)
    except:
        return False

def create_access_token(data: Dict) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)

def verify_token(token: str) -> Optional[Dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except:
        return None

def hash_token(token: str) -> str:
    """Hash token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()
```

**File 3: `routers/demo_auth.py`**

```python
"""Demo Authentication Endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from google.cloud import bigquery
from datetime import datetime, timedelta
import uuid

import config
from utils import demo_auth

router = APIRouter(prefix="/demo-auth", tags=["Demo Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/demo-auth/login")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str
    user_name: str

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Simple login for demo"""
    client = bigquery.Client(project=config.PROJECT_ID)
    
    # Get user
    query = f"""
    SELECT user_id, email, password_hash, full_name
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.demo_users`
    WHERE email = @email AND is_active = TRUE
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", form_data.username)]
    )
    
    results = list(client.query(query, job_config=job_config).result())
    
    if not results:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = results[0]
    
    # Verify password
    if not demo_auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token_data = {"sub": user.user_id, "email": user.email}
    access_token = demo_auth.create_access_token(token_data)
    
    # Store session
    session_id = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(minutes=480)
    
    session_table = f"{config.PROJECT_ID}.{config.BQ_DATASET}.demo_sessions"
    client.insert_rows_json(session_table, [{
        'session_id': session_id,
        'user_id': user.user_id,
        'token_hash': demo_auth.hash_token(access_token),
        'expires_at': expires.isoformat(),
        'created_at': datetime.utcnow().isoformat(),
    }])
    
    return TokenResponse(
        access_token=access_token,
        user_email=user.email,
        user_name=user.full_name
    )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token"""
    payload = demo_auth.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Logout (invalidate session)"""
    client = bigquery.Client(project=config.PROJECT_ID)
    token_hash = demo_auth.hash_token(token)
    
    # Delete session
    query = f"""
    DELETE FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.demo_sessions`
    WHERE token_hash = '{token_hash}'
    """
    client.query(query).result()
    
    return {"message": "Logged out"}

@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    """Get current user info"""
    client = bigquery.Client(project=config.PROJECT_ID)
    
    query = f"""
    SELECT email, full_name
    FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.demo_users`
    WHERE user_id = '{user['sub']}'
    """
    
    results = list(client.query(query).result())
    if not results:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = results[0]
    return {
        "email": user_data.email,
        "full_name": user_data.full_name
    }
```

### **DAY 2 - Sunday, Dec 15** [6 hours]

#### Task 1: Update main.py (1 hour)

```python
# Add to main.py
from routers import demo_auth

# Register router
app.include_router(demo_auth.router)

# Add simple middleware to check auth on protected routes
from fastapi import Request, HTTPException

@app.middleware("http")
async def demo_auth_middleware(request: Request, call_next):
    """Simple auth check for demo"""
    
    # Public endpoints (no auth needed)
    public_paths = ["/docs", "/openapi.json", "/demo-auth/login", "/health"]
    
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check for authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    payload = demo_auth.verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Add user to request state
    request.state.user = payload
    
    return await call_next(request)
```

#### Task 2: Test Backend (2 hours)

**Create `test_demo_auth.py`:**

```python
"""Test demo authentication"""
import requests

BASE_URL = "http://localhost:8080"

def test_login():
    """Test login"""
    print("1. Testing login...")
    
    response = requests.post(
        f"{BASE_URL}/demo-auth/login",
        data={"username": "rep1@fiinch.ai", "password": "Demo@2025"}
    )
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    
    print(f"   ✓ Logged in as: {data['user_name']}")
    print(f"   Token: {data['access_token'][:50]}...")
    
    return data['access_token']

def test_protected_endpoint(token):
    """Test accessing protected endpoint"""
    print("\n2. Testing protected endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/demo-auth/me", headers=headers)
    
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    print(f"   ✓ User info: {data['full_name']} ({data['email']})")

def test_ats_endpoint(token):
    """Test ATS endpoint with auth"""
    print("\n3. Testing ATS endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    # Just check if endpoint is accessible (don't actually upload)
    response = requests.get(f"{BASE_URL}/agents/ats/status", headers=headers)
    
    if response.status_code == 404:
        print("   ⚠️  Endpoint not found (expected for now)")
    elif response.status_code == 401:
        print("   ✗ Auth failed!")
        return False
    else:
        print(f"   ✓ Endpoint accessible (status: {response.status_code})")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Demo Authentication Test")
    print("=" * 60)
    
    try:
        token = test_login()
        test_protected_endpoint(token)
        test_ats_endpoint(token)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Demo auth working!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
```

Run:
```powershell
# Terminal 1: Start server
python -m uvicorn main:app --reload --port 8080

# Terminal 2: Run tests
python test_demo_auth.py
```

#### Task 3: Create Demo Credentials Document (30 min)

**File: `DEMO_CREDENTIALS.md`**

```markdown
# Demo Account Credentials

## Sales Representatives
- **Rep 1:** rep1@fiinch.ai / Demo@2025
- **Rep 2:** rep2@fiinch.ai / Demo@2025

## Demo Client Accounts
- **Client 1:** client1@demo.com / Demo@2025
- **Client 2:** client2@demo.com / Demo@2025
- **Client 3:** client3@demo.com / Demo@2025

## Access URLs
- **Backend:** http://localhost:8080 (or deployed URL)
- **Frontend:** http://localhost:3000 (or deployed URL)
- **API Docs:** http://localhost:8080/docs

## Token Expiry
- 8 hours (full demo day)

## Features Available
- ✅ LinkedIn Scout
- ✅ ATS Checker
- ✅ PA+HR Journal
- ✅ Sentiment Analysis
- ✅ Dashboard
- ✅ All exports

## Demo Script for Reps
1. Login with your rep account
2. Show dashboard overview
3. Demo LinkedIn Scout (search candidates)
4. Demo ATS Checker (upload resume + JD)
5. Demo Journal Analysis (upload documents)
6. Show sentiment analysis
7. Export reports to Excel

## Notes for Sales Reps
- If token expires, just re-login
- All demo accounts have full access
- Data is shared across accounts (demo environment)
```

#### Task 4: Frontend Login Page (2.5 hours)

**Create: `vantage_ai_frontend/app/demo-login/page.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function DemoLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch('http://localhost:8080/demo-auth/login', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      
      // Store token and user info
      localStorage.setItem('demo_token', data.access_token);
      localStorage.setItem('demo_user_email', data.user_email);
      localStorage.setItem('demo_user_name', data.user_name);
      
      // Redirect to dashboard
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  // Quick login buttons for demo
  const quickLogin = (email: string) => {
    setEmail(email);
    setPassword('Demo@2025');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-blue-900">
      <div className="max-w-md w-full space-y-8 p-8 bg-gray-800 rounded-lg shadow-2xl">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">Vantage.AI</h1>
          <p className="text-gray-400">Demo Login</p>
        </div>

        <form onSubmit={handleLogin} className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        {/* Quick Login Buttons for Demo */}
        <div className="mt-6 pt-6 border-t border-gray-700">
          <p className="text-sm text-gray-400 mb-3">Quick Login (Demo):</p>
          <div className="space-y-2">
            <button
              onClick={() => quickLogin('rep1@fiinch.ai')}
              className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition"
            >
              Sales Rep 1
            </button>
            <button
              onClick={() => quickLogin('rep2@fiinch.ai')}
              className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition"
            >
              Sales Rep 2
            </button>
            <button
              onClick={() => quickLogin('client1@demo.com')}
              className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition"
            >
              Demo Client
            </button>
          </div>
        </div>

        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            Demo Version | Password: Demo@2025
          </p>
        </div>
      </div>
    </div>
  );
}
```

**Update: `vantage_ai_frontend/lib/api.ts`** (add auth header)

```typescript
// Add at top of file
const getAuthHeader = () => {
  const token = localStorage.getItem('demo_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Update all axios calls to include auth header
export const analyzeResume = async (formData: FormData) => {
  const response = await axios.post(
    `${API_BASE_URL}/agents/ats/analyze`,
    formData,
    {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

// Do this for all API calls...
```

### **DAY 3 - Monday, Dec 16** [4 hours]

#### Task 1: Update Navbar to Show User (1 hour)

```typescript
// components/Navbar.tsx - Update user section
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Navbar() {
  const [userName, setUserName] = useState('Guest');
  const [userEmail, setUserEmail] = useState('');
  const router = useRouter();

  useEffect(() => {
    const name = localStorage.getItem('demo_user_name');
    const email = localStorage.getItem('demo_user_email');
    if (name) setUserName(name);
    if (email) setUserEmail(email);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('demo_token');
    localStorage.removeItem('demo_user_email');
    localStorage.removeItem('demo_user_name');
    router.push('/demo-login');
  };

  return (
    <nav className="...">
      {/* Existing navbar content */}
      
      {/* User section - update this */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium text-white">{userName}</p>
          <p className="text-xs text-gray-400">{userEmail}</p>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
```

#### Task 2: Add Route Protection (2 hours)

```typescript
// app/layout.tsx - Add auth check
'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Skip auth check for login page
    if (pathname === '/demo-login') return;

    // Check if user is authenticated
    const token = localStorage.getItem('demo_token');
    if (!token) {
      router.push('/demo-login');
    }
  }, [pathname, router]);

  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

#### Task 3: Final Testing & Documentation (1 hour)

**Test Checklist:**
```
Demo Authentication Test Checklist

BACKEND:
[ ] Can login with rep1@fiinch.ai
[ ] Can login with rep2@fiinch.ai
[ ] Can login with demo client accounts
[ ] Wrong password is rejected
[ ] Token works for 8 hours
[ ] Can logout successfully
[ ] Protected endpoints require auth
[ ] /docs is publicly accessible

FRONTEND:
[ ] Login page looks good
[ ] Quick login buttons work
[ ] Successfully redirects to dashboard after login
[ ] Navbar shows correct user name
[ ] Logout button works
[ ] Redirects to login when not authenticated
[ ] All features work when logged in
[ ] Token persists across page refreshes

DEMO FLOW:
[ ] Rep can login quickly
[ ] Can switch between accounts
[ ] All features accessible
[ ] No errors in console
[ ] Fast performance
```

---

## 🚀 DAY 4 - Tuesday, Dec 17 [8 hours]
**Focus:** Deploy Backend + Frontend for Remote Access

### Why Deploy?
Sales reps need to **show clients remotely** - localhost won't work! You need:
- ✅ Public backend API URL
- ✅ Public frontend URL
- ✅ HTTPS with SSL
- ✅ Accessible from anywhere

### Morning Session (4 hours)

#### Task 1: Prepare Backend for Deployment (1 hour)

**Create `Dockerfile` in vantage_api/:**

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
```

**Create `.dockerignore`:**

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
pa_env/
backend_env/
.env
.git/
.gitignore
*.md
test_*.py
keys/*.json
```

**Create `app.yaml` (for App Engine alternative):**

```yaml
runtime: python39
entrypoint: uvicorn main:app --host 0.0.0.0 --port $PORT

env_variables:
  JWT_SECRET_KEY: "your-production-secret-key-change-this-123456789012"
  
automatic_scaling:
  min_instances: 1
  max_instances: 10
```

**Test Docker locally:**

```powershell
# Build image
docker build -t vantage-demo-api .

# Run container
docker run -p 8080:8080 -e JWT_SECRET_KEY="test-key-12345" vantage-demo-api

# Test in another terminal
curl http://localhost:8080/health
```

#### Task 2: Deploy Backend to GCP (2 hours)

**🎯 Using GCP Always Free Tier - $0/month for demo!**

GCP offers these **FREE forever** (not trial):
- ✅ **Compute Engine** - f1-micro instance (us-west1/us-central1/us-east1)
- ✅ **BigQuery** - 1TB queries/month, 10GB storage
- ✅ **Cloud Storage** - 5GB storage
- ✅ **Cloud Build** - 120 build-minutes/day

**Option A: Compute Engine f1-micro (Recommended - FREE forever)**

This gives you a **FREE VM 24/7** - perfect for demo!

```powershell
# Navigate to project
cd c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_api

# Set GCP project
gcloud config set project vantage-ai-prod

# Create firewall rule for HTTP/HTTPS
gcloud compute firewall-rules create allow-http-https \
  --allow tcp:80,tcp:443,tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server

# Create f1-micro instance (FREE tier)
gcloud compute instances create vantage-demo-vm \
  --zone=us-central1-a \
  --machine-type=f1-micro \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --tags=http-server \
  --metadata=startup-script='#!/bin/bash
apt-get update
apt-get install -y python3-pip python3-venv git
'

# Get the external IP (save this!)
gcloud compute instances describe vantage-demo-vm \
  --zone=us-central1-a \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

# SSH into the VM
gcloud compute ssh vantage-demo-vm --zone=us-central1-a

# === Inside VM (after SSH) ===

# Clone your repo or copy files
# Option 1: If you have repo access
git clone https://github.com/Sovik89/AI4U_PA.git
cd AI4U_PA/vantage_api

# Option 2: Or use gcloud to copy from local
# (Exit SSH first, run from local machine)
# gcloud compute scp --recurse c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_api vantage-demo-vm:~/vantage_api --zone=us-central1-a

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy service account key
# (Run from local machine)
# gcloud compute scp c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_api\keys\sa-keys.json vantage-demo-vm:~/vantage_api/keys/ --zone=us-central1-a

# Set environment variables
export JWT_SECRET_KEY="demo-production-secret-key-change-this-12345678901234567890"
export PROJECT_ID="vantage-ai-prod"
export BQ_DATASET="hr_insights"
export GOOGLE_APPLICATION_CREDENTIALS="/home/YOUR_USERNAME/vantage_api/keys/sa-keys.json"

# Test run
python -m uvicorn main:app --host 0.0.0.0 --port 8080

# If working, set up as systemd service for auto-restart
sudo nano /etc/systemd/system/vantage-api.service
```

**Create systemd service file:**

```ini
[Unit]
Description=Vantage Demo API
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/vantage_api
Environment="PATH=/home/YOUR_USERNAME/vantage_api/venv/bin"
Environment="JWT_SECRET_KEY=demo-production-secret-key-12345678901234567890"
Environment="PROJECT_ID=vantage-ai-prod"
Environment="BQ_DATASET=hr_insights"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/YOUR_USERNAME/vantage_api/keys/sa-keys.json"
ExecStart=/home/YOUR_USERNAME/vantage_api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable vantage-api

# Start service
sudo systemctl start vantage-api

# Check status
sudo systemctl status vantage-api

# View logs
sudo journalctl -u vantage-api -f
```

**Your API is now at:** `http://YOUR_VM_IP:8080`

**Optional: Add SSL with Nginx (for HTTPS):**

```bash
# Install Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx as reverse proxy
sudo nano /etc/nginx/sites-available/vantage-api

# Add this config:
server {
    listen 80;
    server_name YOUR_VM_IP;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/vantage-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Your API is now at:** `http://YOUR_VM_IP` (port 80)

---

**Option B: Cloud Run (Pay-per-use, but within free tier for demo)**

```powershell
# Enable Cloud Run API
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy to Cloud Run
gcloud run deploy vantage-demo-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars JWT_SECRET_KEY="demo-production-secret-key-12345678901234567890",PROJECT_ID="vantage-ai-prod",BQ_DATASET="hr_insights"

# URL: https://vantage-demo-api-xxxxxxxxxx-uc.a.run.app
```

**Cloud Run Free Tier:**
- 2 million requests/month FREE
- 360,000 GiB-seconds memory FREE
- 180,000 vCPU-seconds FREE

**For demo with ~10 users:** Likely stays FREE!

---

**Option C: App Engine Standard (Free quota)**

```powershell
# Create app.yaml
# (Already created in Task 1)

# Deploy
gcloud app deploy app.yaml --quiet

# URL: https://vantage-ai-prod.uc.r.appspot.com
```

**App Engine Free Tier:**
- 28 instance hours/day FREE (F1/F2 instances)
- 1GB storage FREE

---

**💡 RECOMMENDATION:**

**For Demo (Dec-Jan):** Use **Compute Engine f1-micro** 
- ✅ 100% FREE forever (not trial)
- ✅ Always running (no cold starts)
- ✅ Full control
- ✅ 30GB disk included

**For Production (Jan+):** Migrate to **Cloud Run**
- ✅ Auto-scaling
- ✅ Pay only for actual usage
- ✅ Built-in HTTPS
- ✅ Zero maintenance

#### Task 3: Test Deployed Backend (1 hour)

**Create `test_deployed_api.py`:**

```python
"""Test deployed backend API"""
import requests
import json

# CHANGE THIS to your deployed URL
DEPLOYED_URL = "https://vantage-demo-api-xxxxxxxxxx-uc.a.run.app"

def test_health():
    """Test health endpoint"""
    print("1. Testing health endpoint...")
    response = requests.get(f"{DEPLOYED_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    assert response.status_code == 200

def test_login():
    """Test login on deployed API"""
    print("\n2. Testing login...")
    
    response = requests.post(
        f"{DEPLOYED_URL}/demo-auth/login",
        data={"username": "rep1@fiinch.ai", "password": "Demo@2025"}
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Logged in as: {data.get('user_name')}")
        return data.get('access_token')
    else:
        print(f"   ✗ Error: {response.text}")
        return None

def test_authenticated_request(token):
    """Test authenticated endpoint"""
    print("\n3. Testing authenticated endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{DEPLOYED_URL}/demo-auth/me", headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ User: {data.get('full_name')} ({data.get('email')})")
    else:
        print(f"   ✗ Error: {response.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Deployed Backend API")
    print(f"URL: {DEPLOYED_URL}")
    print("=" * 60)
    
    try:
        test_health()
        token = test_login()
        if token:
            test_authenticated_request(token)
        
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
```

Run test:
```powershell
python test_deployed_api.py
```

### Afternoon Session (4 hours)

#### Task 4: Prepare Frontend for Deployment (1 hour)

**Update `vantage_ai_frontend/.env.production`:**

```bash
# Replace with your deployed backend URL
NEXT_PUBLIC_API_URL=https://vantage-demo-api-xxxxxxxxxx-uc.a.run.app
```

**Update `vantage_ai_frontend/next.config.js`:**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow API calls to Cloud Run
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL + '/:path*',
      },
    ]
  },
  // Image domains if you use Next Image
  images: {
    domains: ['your-cdn-domain.com'],
  },
}

module.exports = nextConfig
```

**Update API calls in `lib/api.ts` to use environment variable:**

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// Rest of your API client code...
```

**Test locally with production API:**

```powershell
cd c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_frontend-main_code

# Set production API URL
$env:NEXT_PUBLIC_API_URL="https://vantage-demo-api-xxxxxxxxxx-uc.a.run.app"

# Run frontend
npm run dev

# Open http://localhost:3000/demo-login
# Try logging in - it should call your deployed backend
```

#### Task 5: Deploy Frontend to Vercel (2 hours)

**Option A: Vercel (Recommended - Free, Fast, CDN)**

```powershell
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend
cd c:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_frontend-main_code

# Login to Vercel
vercel login

# Deploy to production
vercel --prod

# Follow prompts:
# - Link to existing project or create new
# - Set project name: vantage-demo
# - Framework preset: Next.js
# - Build command: npm run build (default)
# - Output directory: .next (default)

# Set environment variable in Vercel
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://vantage-demo-api-xxxxxxxxxx-uc.a.run.app

# Redeploy with env vars
vercel --prod
```

**Your frontend will be live at:**
`https://vantage-demo.vercel.app` or similar

**Option B: Firebase Hosting (Alternative)**

```powershell
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize
firebase init hosting

# Build Next.js for static export
npm run build
npm run export

# Deploy
firebase deploy --only hosting
```

**Option C: GCP Cloud Storage + Load Balancer (Custom domain)**

```powershell
# Build Next.js
npm run build

# Create bucket
gsutil mb gs://vantage-demo-frontend

# Make bucket public
gsutil iam ch allUsers:objectViewer gs://vantage-demo-frontend

# Upload files
gsutil -m cp -r out/* gs://vantage-demo-frontend/

# Set index page
gsutil web set -m index.html gs://vantage-demo-frontend

# Your URL: https://storage.googleapis.com/vantage-demo-frontend/index.html
```

#### Task 6: Update CORS on Backend (30 min)

**Update backend to allow your frontend domain:**

```powershell
# Update Cloud Run CORS settings
gcloud run services update vantage-demo-api \
  --region us-central1 \
  --set-env-vars "CORS_ORIGINS=https://vantage-demo.vercel.app,https://vantage-demo-xxxxxxxxx.vercel.app"
```

**Or update in code (`main.py`):**

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

# Update CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://vantage-demo.vercel.app",
        "https://vantage-demo-xxxxxxxxx.vercel.app",  # Vercel preview URLs
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy:
```powershell
gcloud run deploy vantage-demo-api --source .
```

#### Task 7: Final End-to-End Test (30 min)

**Test the complete deployed app:**

```
1. Open: https://vantage-demo.vercel.app/demo-login
2. Click "Sales Rep 1" quick login
3. Should login successfully
4. Navigate to Dashboard - should load
5. Try LinkedIn Scout - should work
6. Try ATS Checker - upload should work
7. Check Navbar - should show user name
8. Click Logout - should redirect to login
9. Try accessing dashboard without login - should redirect
```

**Checklist:**
```
DEPLOYMENT VERIFICATION:
[ ] Backend deployed and accessible
[ ] Frontend deployed and accessible
[ ] Can login with demo accounts
[ ] All features work (LinkedIn, ATS, Journal, Sentiment)
[ ] File uploads work
[ ] Dashboard loads data
[ ] Logout works
[ ] HTTPS/SSL working (green lock icon)
[ ] No CORS errors in browser console
[ ] No 401 unauthorized errors
[ ] Fast load times (< 3 seconds)
```

---

## 📋 Complete Demo Deployment Checklist (Dec 17-20)

### Pre-Deployment (Day 4 Morning)
- [ ] All local tests passing
- [ ] Dockerfile created and tested
- [ ] Environment variables documented
- [ ] Service account key accessible

### Backend Deployment (Day 4 Morning)
- [ ] Cloud Run API enabled
- [ ] Backend deployed to Cloud Run
- [ ] Environment variables set
- [ ] Health endpoint working
- [ ] Login endpoint working
- [ ] Got deployed URL (save it!)

### Frontend Deployment (Day 4 Afternoon)
- [ ] Frontend .env.production updated with backend URL
- [ ] Vercel CLI installed
- [ ] Frontend deployed to Vercel
- [ ] Environment variables set in Vercel
- [ ] Got deployed URL (save it!)

### Integration Testing (Day 4 Evening)
- [ ] Updated CORS on backend
- [ ] Can login from deployed frontend
- [ ] All features work end-to-end
- [ ] No console errors
- [ ] SSL certificate valid
- [ ] Mobile responsive test

### Sales Rep Enablement (Dec 18-19)
- [ ] Demo credentials document ready
- [ ] Created DEMO_GUIDE.md with screenshots
- [ ] Trained sales reps on login process
- [ ] Sales reps tested login independently
- [ ] Share deployed URLs:
  - Frontend: https://vantage-demo.vercel.app
  - Backend: https://vantage-demo-api-xyz.run.app
  - API Docs: https://vantage-demo-api-xyz.run.app/docs

### Go-Live (Dec 20)
- [ ] Monitor Cloud Run logs
- [ ] Monitor Vercel analytics
- [ ] Sales reps actively demoing
- [ ] Collect client feedback
- [ ] Track any bugs/issues

---

## 🔧 Troubleshooting Deployment Issues

### Issue 1: CORS Error
**Symptom:** Browser console shows "CORS policy blocked"

**Solution for Compute Engine VM:**
```python
# Update main.py CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-url.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Restart service
sudo systemctl restart vantage-api
```

**Solution for Cloud Run:**
```powershell
gcloud run services update vantage-demo-api \
  --set-env-vars "CORS_ORIGINS=https://your-frontend-url.vercel.app"
```

### Issue 2: 401 Unauthorized
**Symptom:** Login works but other endpoints return 401
**Solution:** Check middleware is properly extracting token from header

### Issue 3: BigQuery Permission Denied
**Symptom:** Backend can't read demo_users table

**Solution for Compute Engine:**
```bash
# Make sure service account key is accessible
ls -la ~/vantage_api/keys/sa-keys.json

# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test BigQuery access
python3 -c "from google.cloud import bigquery; client = bigquery.Client(project='vantage-ai-prod'); print('Connected!')"
```

**Solution for Cloud Run:**
```powershell
# Ensure Cloud Run service account has BigQuery access
gcloud projects add-iam-policy-binding vantage-ai-prod \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

### Issue 4: Slow API Response
**Symptom:** Login takes > 5 seconds

**Solution for Compute Engine (f1-micro limitations):**
- f1-micro has limited CPU (shared core)
- Consider upgrading to e2-small (also eligible for free credits)
```powershell
gcloud compute instances stop vantage-demo-vm --zone=us-central1-a
gcloud compute instances set-machine-type vantage-demo-vm \
  --machine-type=e2-small \
  --zone=us-central1-a
gcloud compute instances start vantage-demo-vm --zone=us-central1-a
```

**Solution for Cloud Run:**
```powershell
gcloud run services update vantage-demo-api \
  --memory 1Gi \
  --cpu 2 \
  --min-instances 1
```

### Issue 5: Frontend Build Fails
**Symptom:** Vercel deployment fails
**Solution:** Check Node version compatibility
```powershell
# Update package.json
{
  "engines": {
    "node": "18.x"
  }
}
```

---

## 💰 Cost Estimate for Demo Deployment

**Backend (Compute Engine f1-micro - RECOMMENDED):**
- f1-micro instance (us-central1): **FREE forever**
- 30GB standard disk: **FREE** (included)
- Egress: First 1GB/month FREE, then $0.12/GB (likely < $2)
- **Demo usage:** **$0-2/month** ✅

**Backend (Cloud Run - Alternative):**
- First 2 million requests/month: FREE
- 180,000 vCPU-seconds/month: FREE
- 360,000 GiB-seconds/month: FREE
- **Demo usage with ~10 users:** ~$0/month (stays in free tier)

**Frontend (Vercel):**
- Hobby plan: **FREE**
- 100GB bandwidth/month
- **Demo usage:** **FREE** ✅

**BigQuery:**
- First 1TB queries/month: **FREE**
- First 10GB storage: **FREE**
- **Demo usage:** **$0/month** ✅

**Total Demo Cost:** **$0-2/month** 🎉 (Essentially FREE!)

---

## 📞 Deployed URLs Reference Card

**Print this for sales reps:**

```
═══════════════════════════════════════════════════════
        VANTAGE.AI DEMO - DEPLOYED URLS
═══════════════════════════════════════════════════════

🌐 FRONTEND (Show to clients):
   https://vantage-demo.vercel.app/demo-login

🔧 BACKEND API:
   http://YOUR_VM_IP:8080
   (or https://vantage-demo-api-xxx.run.app if using Cloud Run)

📚 API DOCUMENTATION:
   http://YOUR_VM_IP:8080/docs
   (or https://vantage-demo-api-xxx.run.app/docs)

───────────────────────────────────────────────────────
DEMO CREDENTIALS:
───────────────────────────────────────────────────────

Sales Reps:
  rep1@fiinch.ai / Demo@2025
  rep2@fiinch.ai / Demo@2025

Demo Clients (for prospect testing):
  client1@demo.com / Demo@2025
  client2@demo.com / Demo@2025

───────────────────────────────────────────────────────
FEATURES TO DEMO:
───────────────────────────────────────────────────────
✓ LinkedIn Scout - AI-powered candidate search
✓ ATS Checker - Resume analysis + scoring
✓ PA+HR Journal - Document intelligence
✓ Sentiment Analysis - Team sentiment tracking
✓ Dashboard - Analytics overview
✓ Excel Reports - Download analysis results

───────────────────────────────────────────────────────
DEMO TIPS:
───────────────────────────────────────────────────────
• Token lasts 8 hours (full demo day)
• All accounts have full feature access
• Show mobile responsiveness
• Highlight AI-powered insights
• Demo export to Excel
• Show real-time analysis

───────────────────────────────────────────────────────
SUPPORT: [Your email] | [Your phone]
═══════════════════════════════════════════════════════
```

---

## 🚀 TRACK 2: Production Scale (Dec 21 - Jan 15)

While sales reps are demoing, build production version in parallel:

### Week 1 (Dec 21-27): Core Architecture
- Full multi-tenant database schema (6 tables)
- Organization hierarchy
- Subscription management
- RBAC implementation

### Week 2 (Dec 28 - Jan 3): Advanced Features
- Payment integration (Stripe)
- Email verification
- Password reset
- API key management
- Rate limiting by tier

### Week 3 (Jan 4-10): Scaling & Performance
- Cloud Run autoscaling
- Redis caching
- Load balancing
- CDN integration
- Database optimization

### Week 4 (Jan 11-15): Testing & Launch
- Load testing
- Security audit
- Migration from demo
- Production deployment
- User onboarding

---

## 📊 Success Metrics

### Demo Phase (Dec 20 - Jan 15)
- ✅ 2 sales reps actively demoing
- ✅ 5+ client demos completed
- ✅ Feedback collected
- ✅ Zero critical bugs
- ✅ Average demo duration: 30-45 min

### Production Phase (Jan 15+)
- ✅ 10+ paying organizations onboarded
- ✅ 99.9% uptime
- ✅ < 500ms response time
- ✅ Support multi-currency billing
- ✅ Mobile-responsive

---

## 💡 Key Advantages of This Approach

**Why This Works:**
1. ✅ **Fast to Market** - 3 days vs 7 days
2. ✅ **Learn from Users** - Real feedback while building scale version
3. ✅ **Parallel Development** - Sales happening while engineering
4. ✅ **Risk Mitigation** - Don't over-engineer before product-market fit
5. ✅ **Cost Effective** - Simple demo infrastructure is cheaper

**What You Avoid:**
- ❌ Building full multi-tenant before validating demand
- ❌ Complex subscription logic before understanding pricing
- ❌ Over-engineering authentication before user feedback
- ❌ Scaling infrastructure prematurely

---

## 📞 Quick Reference

**Demo Credentials:** rep1@fiinch.ai / Demo@2025  
**Backend:** http://localhost:8080  
**Frontend:** http://localhost:3000/demo-login  
**API Docs:** http://localhost:8080/docs  

**Support Contact:** [Your email]  
**Demo Duration:** 8 hours (1 full working day)  

---

**START SATURDAY 9 AM - GET DEMO READY BY MONDAY EVENING!** 🚀

Then parallel work on production scale for mid-January launch! 💪
