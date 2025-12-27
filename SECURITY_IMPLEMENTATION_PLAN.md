# Vantage.AI Security & Authentication Implementation Plan
## Complete Registration, Login & Role-Based Access Control (RBAC)

**Project:** Vantage.AI Platform - Production Security Implementation  
**Timeline:** December 14-31, 2025 (18 days)  
**Owner:** Fiinch.ai  
**Status:** 🎯 READY TO START - December 14, 2025  
**Document Version:** 1.0  
**Last Updated:** December 13, 2025  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [User Hierarchy & Access Matrix](#user-hierarchy--access-matrix)
4. [Phase 1: Database Schema (Days 1-3)](#phase-1-database-schema-days-1-3)
5. [Phase 2: Backend Authentication (Days 4-8)](#phase-2-backend-authentication-days-4-8)
6. [Phase 3: Middleware & Security (Days 9-11)](#phase-3-middleware--security-days-9-11)
7. [Phase 4: Frontend Integration (Days 12-15)](#phase-4-frontend-integration-days-12-15)
8. [Phase 5: Testing & Deployment (Days 16-18)](#phase-5-testing--deployment-days-16-18)
9. [Daily Task Breakdown](#daily-task-breakdown)
10. [Code Templates](#code-templates)
11. [Testing Checklist](#testing-checklist)
12. [Security Best Practices](#security-best-practices)
13. [Troubleshooting Guide](#troubleshooting-guide)
14. [Post-Launch Monitoring](#post-launch-monitoring)

---

## 📋 Executive Summary

### Current State
- **No Authentication:** All users access as "guest@vantage.ai"
- **No Authorization:** No role-based access control
- **No User Management:** No registration or login system
- **Security Risk:** Open API endpoints with no protection

### Target State
- **Secure Authentication:** JWT-based login with bcrypt password hashing
- **Role-Based Access Control:** 3 user types with distinct permissions
- **Multi-Tenant Support:** Organization-based subscriptions with tiered access
- **Audit Trail:** Complete logging of all security events
- **Production Ready:** Rate limiting, session management, security headers

### Business Requirements

**User Types:**
1. **Platform Owner (Fiinch.ai)** - Full administrative access
2. **Freelancers** - Limited view-only access to core features
3. **Organizations** - Full access with tiered subscription plans (Basic/Gold/Premium)

**Timeline:** 18 days (December 14-31, 2025)  
**Budget:** Internal development (100 estimated hours)  
**Success Criteria:** 
- Zero security vulnerabilities
- < 500ms authentication response time
- 99.9% uptime
- Seamless migration of existing data

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Login Page   │  │ Register Page│  │ Protected Routes   │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                           │                                      │
│                    AuthContext (JWT)                            │
└───────────────────────────┼─────────────────────────────────────┘
                            │ HTTPS + JWT Bearer Token
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                            │  │
│  │  • Rate Limiter (slowapi)                               │  │
│  │  • Auth Middleware (JWT validation)                     │  │
│  │  • RBAC Middleware (permission checks)                  │  │
│  │  • Audit Logger                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  API Routers                             │  │
│  │  /auth/* (public)    /users/* (protected)              │  │
│  │  /ats/* (protected)  /sentiment/* (protected)          │  │
│  │  /linkedin/* (protected) /journal/* (protected)        │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BigQuery (hr_insights dataset)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   users      │  │organizations │  │   user_sessions      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   roles      │  │  user_roles  │  │   audit_logs         │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌────────────┐                                      ┌────────────┐
│  Frontend  │                                      │  Backend   │
└─────┬──────┘                                      └─────┬──────┘
      │                                                   │
      │  1. POST /auth/login                             │
      │     {email, password}                            │
      ├─────────────────────────────────────────────────>│
      │                                                   │
      │                                2. Verify password │
      │                                3. Check user     │
      │                                   is_active      │
      │                                4. Get permissions│
      │                                5. Create JWT     │
      │                                                   │
      │  6. Return tokens + user data + permissions      │
      │<─────────────────────────────────────────────────┤
      │     {access_token, refresh_token, user, perms}   │
      │                                                   │
      │  7. Store in localStorage                        │
      │                                                   │
      │  8. GET /ats/analyze                             │
      │     Authorization: Bearer <token>                │
      ├─────────────────────────────────────────────────>│
      │                                                   │
      │                              9. Validate JWT     │
      │                              10. Check permission│
      │                              11. Process request │
      │                                                   │
      │  12. Return protected data                       │
      │<─────────────────────────────────────────────────┤
      │                                                   │
```

### JWT Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id_uuid",
    "email": "user@example.com",
    "user_type": "organization",
    "organization_id": "org_id_uuid",
    "type": "access",
    "exp": 1735689600,
    "iat": 1735687800
  },
  "signature": "..."
}
```

---

## 🎯 User Hierarchy & Access Matrix

### User Types Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                    PLATFORM OWNER                       │
│                      Fiinch.ai                          │
│              admin@fiinch.ai (role_owner)               │
│                                                         │
│  Permissions: ALL (Full System Admin)                  │
│  • Manage all users and organizations                  │
│  • View audit logs                                     │
│  • Change subscriptions                                │
│  • Access all features                                 │
└─────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
┌─────────▼───────────┐           ┌──────────▼──────────┐
│    FREELANCERS      │           │   ORGANIZATIONS     │
│   (Individual)      │           │    (Companies)      │
│ role_freelancer     │           │  Tiered Plans       │
├─────────────────────┤           ├─────────────────────┤
│ Permissions:        │           │ Permissions:        │
│ ✓ LinkedIn Scout    │           │ ✓ All Features      │
│ ✓ ATS Checker       │           │ ✓ Sentiment         │
│ ✓ PA+HR Journal     │           │ ✓ Dashboard         │
│ ✓ View/Read Only    │           │ ✓ Analytics         │
│ ✗ Sentiment         │           │ ✓ Create/Update     │
│ ✗ Dashboard         │           │ ✓ Export (Gold+)    │
│ ✗ Export            │           │ ✓ API (Premium)     │
│                     │           └─────────────────────┘
│ Limits:             │                      │
│ • 10 jobs/month     │        ┌─────────────┼─────────────┐
│ • 1 GB storage      │        │             │             │
│ • No API access     │   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
└─────────────────────┘   │  BASIC  │  │  GOLD   │  │ PREMIUM │
                          │  $29/mo │  │  $99/mo │  │ $299/mo │
                          ├─────────┤  ├─────────┤  ├─────────┤
                          │ 5 users │  │ 20 users│  │Unlimited│
                          │100 jobs │  │500 jobs │  │Unlimited│
                          │ 10 GB   │  │ 50 GB   │  │ 200 GB  │
                          │No Export│  │✓ Export │  │✓ Export │
                          │No API   │  │No API   │  │✓ API    │
                          └─────────┘  └─────────┘  └─────────┘
```

### Complete Access Matrix

| Feature / Permission | Owner | Freelancer | Basic | Gold | Premium |
|---------------------|-------|-----------|-------|------|---------|
| **Features** | | | | | |
| LinkedIn Scout | ✅ Full | ✅ View | ✅ Full | ✅ Full | ✅ Full |
| ATS Checker | ✅ Full | ✅ View | ✅ Full | ✅ Full | ✅ Full |
| PA+HR Journal | ✅ Full | ✅ View | ✅ Full | ✅ Full | ✅ Full |
| Sentiment Analysis | ✅ Full | ❌ | ✅ Basic | ✅ Advanced | ✅ Advanced |
| Dashboard | ✅ Full | ❌ | ✅ Basic | ✅ Advanced | ✅ Full Analytics |
| Analytics Reports | ✅ Full | ❌ | ❌ | ✅ | ✅ |
| **Actions** | | | | | |
| Create/Upload | ✅ | ❌ | ✅ | ✅ | ✅ |
| Read/View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update/Edit | ✅ | ❌ | ✅ | ✅ | ✅ |
| Delete | ✅ | ❌ | ✅ | ✅ | ✅ |
| Export (Excel/PDF) | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Admin** | | | | | |
| Manage Users | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage Orgs | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Audit Logs | ✅ | ❌ | ❌ | ❌ | ❌ |
| Billing Management | ✅ | N/A | ✅ Owner | ✅ Owner | ✅ Owner |
| **Limits** | | | | | |
| Max Users | Unlimited | 1 | 5 | 20 | Unlimited |
| Monthly Jobs | Unlimited | 10 | 100 | 500 | Unlimited |
| Storage | Unlimited | 1 GB | 10 GB | 50 GB | 200 GB |
| API Access | ✅ | ❌ | ❌ | ❌ | ✅ |
| API Rate Limit | Unlimited | N/A | N/A | N/A | 10,000/day |

---

## 🗄️ Phase 1: Database Schema (Days 1-3)

### Overview
Create 6 new tables in BigQuery to support authentication, authorization, and audit logging. All tables will be in the existing `vantage-ai-prod.hr_insights` dataset.

### Day 1: Core Security Tables

#### Task 1.1: Create Users Table

**Purpose:** Store user accounts with authentication credentials

**SQL Script:**
```sql
-- Create users table
CREATE TABLE `vantage-ai-prod.hr_insights.users` (
    -- Primary key
    user_id STRING NOT NULL OPTIONS(description="UUID v4 unique identifier"),
    
    -- Authentication
    email STRING NOT NULL OPTIONS(description="User email (unique)"),
    password_hash STRING NOT NULL OPTIONS(description="bcrypt hashed password"),
    
    -- Profile
    full_name STRING OPTIONS(description="User full name"),
    phone STRING OPTIONS(description="Phone number"),
    
    -- User classification
    user_type STRING NOT NULL OPTIONS(description="Type: owner, freelancer, organization"),
    organization_id STRING OPTIONS(description="FK to organizations table"),
    
    -- Email verification
    is_active BOOLEAN DEFAULT TRUE OPTIONS(description="Account active status"),
    is_verified BOOLEAN DEFAULT FALSE OPTIONS(description="Email verified"),
    email_verification_token STRING OPTIONS(description="Token for email verification"),
    email_verified_at TIMESTAMP OPTIONS(description="When email was verified"),
    
    -- Security
    last_login_at TIMESTAMP OPTIONS(description="Last successful login"),
    last_login_ip STRING OPTIONS(description="IP address of last login"),
    login_attempts INT64 DEFAULT 0 OPTIONS(description="Failed login counter"),
    locked_until TIMESTAMP OPTIONS(description="Account lock expiration"),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Record creation time"),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Last update time"),
    created_by STRING OPTIONS(description="User who created this account")
)
PARTITION BY DATE(created_at)
OPTIONS(
    description="User accounts and authentication data",
    labels=[("security", "auth"), ("pii", "true")]
);

-- Create indexes
-- Note: BigQuery doesn't support traditional indexes, but we use clustering
ALTER TABLE `vantage-ai-prod.hr_insights.users`
SET OPTIONS (
    clustering_fields="email, user_type, organization_id"
);

-- Verify table creation
SELECT 
    table_name,
    creation_time,
    row_count,
    size_bytes
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id = 'users';
```

**Test Data (for development):**
```sql
-- Insert test owner account (Fiinch.ai)
INSERT INTO `vantage-ai-prod.hr_insights.users` (
    user_id, email, password_hash, full_name, user_type, 
    is_active, is_verified, created_at
) VALUES (
    GENERATE_UUID(),
    'admin@fiinch.ai',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', -- 'Admin@123'
    'Fiinch Admin',
    'owner',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP()
);

-- Insert test freelancer
INSERT INTO `vantage-ai-prod.hr_insights.users` (
    user_id, email, password_hash, full_name, user_type,
    is_active, is_verified, created_at
) VALUES (
    GENERATE_UUID(),
    'freelancer@test.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5xIAkN1rB.yUK', -- 'Test@123'
    'Test Freelancer',
    'freelancer',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP()
);

-- Verify insertion
SELECT user_id, email, full_name, user_type, is_verified, created_at
FROM `vantage-ai-prod.hr_insights.users`
ORDER BY created_at DESC;
```

#### Task 1.2: Create Organizations Table

**Purpose:** Store organization accounts with subscription details

**SQL Script:**
```sql
-- Create organizations table
CREATE TABLE `vantage-ai-prod.hr_insights.organizations` (
    -- Primary key
    organization_id STRING NOT NULL OPTIONS(description="UUID v4 unique identifier"),
    
    -- Organization info
    organization_name STRING NOT NULL OPTIONS(description="Company/organization name"),
    organization_type STRING OPTIONS(description="Type: enterprise, startup, agency, etc."),
    
    -- Owner relationship
    owner_user_id STRING NOT NULL OPTIONS(description="FK to users table - organization admin"),
    
    -- Subscription
    subscription_plan STRING NOT NULL OPTIONS(description="Plan: basic, gold, premium"),
    subscription_status STRING NOT NULL OPTIONS(description="Status: active, trial, suspended, cancelled"),
    subscription_start_date TIMESTAMP OPTIONS(description="Subscription start date"),
    subscription_end_date TIMESTAMP OPTIONS(description="Subscription end date"),
    trial_end_date TIMESTAMP OPTIONS(description="Trial expiration date"),
    
    -- Billing
    billing_email STRING OPTIONS(description="Email for billing"),
    billing_address JSON OPTIONS(description="Billing address details"),
    payment_method_id STRING OPTIONS(description="Stripe payment method ID"),
    last_payment_date TIMESTAMP OPTIONS(description="Last successful payment"),
    next_billing_date TIMESTAMP OPTIONS(description="Next billing date"),
    
    -- Limits
    max_users INT64 DEFAULT 5 OPTIONS(description="Maximum users allowed"),
    current_users INT64 DEFAULT 0 OPTIONS(description="Current user count"),
    max_storage_gb INT64 DEFAULT 10 OPTIONS(description="Storage limit in GB"),
    current_storage_gb FLOAT64 DEFAULT 0 OPTIONS(description="Current storage used"),
    max_monthly_jobs INT64 DEFAULT 100 OPTIONS(description="Monthly job analysis limit"),
    current_monthly_jobs INT64 DEFAULT 0 OPTIONS(description="Jobs analyzed this month"),
    jobs_reset_date DATE OPTIONS(description="Date when job counter resets"),
    
    -- API Access (Premium only)
    api_key STRING OPTIONS(description="Organization API key"),
    api_calls_limit INT64 OPTIONS(description="Daily API call limit"),
    api_calls_used INT64 DEFAULT 0 OPTIONS(description="API calls used today"),
    api_calls_reset_at TIMESTAMP OPTIONS(description="When API counter resets"),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE OPTIONS(description="Organization active status"),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Record creation time"),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Last update time")
)
PARTITION BY DATE(created_at)
CLUSTER BY subscription_plan, subscription_status
OPTIONS(
    description="Organization accounts and subscription management",
    labels=[("business", "subscriptions")]
);

-- Verify creation
SELECT table_name, creation_time, row_count
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id = 'organizations';
```

**Test Data:**
```sql
-- Insert test organization
INSERT INTO `vantage-ai-prod.hr_insights.organizations` (
    organization_id, organization_name, organization_type, owner_user_id,
    subscription_plan, subscription_status, trial_end_date,
    max_users, current_users, api_key, created_at
) VALUES (
    GENERATE_UUID(),
    'Test Company Inc',
    'startup',
    (SELECT user_id FROM `vantage-ai-prod.hr_insights.users` WHERE email = 'freelancer@test.com' LIMIT 1),
    'basic',
    'trial',
    TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 14 DAY),
    5,
    1,
    CONCAT('vantage_', GENERATE_UUID()),
    CURRENT_TIMESTAMP()
);
```

### Day 2: Roles & Permissions Tables

#### Task 1.3: Create Roles Table

**Purpose:** Define role-based permissions for access control

**SQL Script:**
```sql
-- Create roles table
CREATE TABLE `vantage-ai-prod.hr_insights.roles` (
    -- Primary key
    role_id STRING NOT NULL OPTIONS(description="Role identifier"),
    role_name STRING NOT NULL OPTIONS(description="Human-readable role name"),
    description STRING OPTIONS(description="Role description"),
    
    -- Feature permissions (what features user can access)
    can_access_linkedin BOOLEAN DEFAULT FALSE OPTIONS(description="LinkedIn Scout access"),
    can_access_ats BOOLEAN DEFAULT FALSE OPTIONS(description="ATS Checker access"),
    can_access_journal BOOLEAN DEFAULT FALSE OPTIONS(description="PA+HR Journal access"),
    can_access_sentiment BOOLEAN DEFAULT FALSE OPTIONS(description="Sentiment Analysis access"),
    can_access_dashboard BOOLEAN DEFAULT FALSE OPTIONS(description="Dashboard access"),
    can_access_analytics BOOLEAN DEFAULT FALSE OPTIONS(description="Analytics Reports access"),
    
    -- Action permissions (what actions user can perform)
    can_create BOOLEAN DEFAULT TRUE OPTIONS(description="Create new records"),
    can_read BOOLEAN DEFAULT TRUE OPTIONS(description="Read/view records"),
    can_update BOOLEAN DEFAULT FALSE OPTIONS(description="Update existing records"),
    can_delete BOOLEAN DEFAULT FALSE OPTIONS(description="Delete records"),
    can_export BOOLEAN DEFAULT FALSE OPTIONS(description="Export reports (Excel/PDF)"),
    
    -- Admin permissions (administrative actions)
    can_manage_users BOOLEAN DEFAULT FALSE OPTIONS(description="Manage organization users"),
    can_manage_billing BOOLEAN DEFAULT FALSE OPTIONS(description="Manage billing/subscriptions"),
    can_view_audit_logs BOOLEAN DEFAULT FALSE OPTIONS(description="View audit logs"),
    can_manage_organizations BOOLEAN DEFAULT FALSE OPTIONS(description="Manage all organizations (owner only)"),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Role creation time"),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Last update time")
)
OPTIONS(
    description="Role definitions and permissions matrix",
    labels=[("security", "rbac")]
);

-- Pre-populate standard roles
INSERT INTO `vantage-ai-prod.hr_insights.roles` (
    role_id, role_name, description,
    can_access_linkedin, can_access_ats, can_access_journal, 
    can_access_sentiment, can_access_dashboard, can_access_analytics,
    can_create, can_read, can_update, can_delete, can_export,
    can_manage_users, can_manage_billing, can_view_audit_logs, can_manage_organizations
) VALUES
-- Platform Owner (Fiinch.ai)
('role_owner', 'Platform Owner', 'Full system administrator (Fiinch.ai)',
 TRUE, TRUE, TRUE, TRUE, TRUE, TRUE,  -- All features
 TRUE, TRUE, TRUE, TRUE, TRUE,         -- All actions
 TRUE, TRUE, TRUE, TRUE),              -- All admin

-- Freelancer (Limited access)
('role_freelancer', 'Freelancer', 'Individual user with limited access',
 TRUE, TRUE, TRUE, FALSE, FALSE, FALSE,  -- LinkedIn, ATS, Journal only
 FALSE, TRUE, FALSE, FALSE, FALSE,       -- Read-only
 FALSE, FALSE, FALSE, FALSE),            -- No admin

-- Organization: Basic Plan
('role_basic', 'Organization Basic', 'Basic subscription plan features',
 TRUE, TRUE, TRUE, TRUE, TRUE, FALSE,   -- No analytics
 TRUE, TRUE, TRUE, TRUE, FALSE,          -- No export
 FALSE, TRUE, FALSE, FALSE),             -- Billing only

-- Organization: Gold Plan
('role_gold', 'Organization Gold', 'Gold subscription plan features',
 TRUE, TRUE, TRUE, TRUE, TRUE, TRUE,    -- All features
 TRUE, TRUE, TRUE, TRUE, TRUE,           -- All actions including export
 TRUE, TRUE, FALSE, FALSE),              -- User + billing management

-- Organization: Premium Plan
('role_premium', 'Organization Premium', 'Premium subscription plan with API access',
 TRUE, TRUE, TRUE, TRUE, TRUE, TRUE,    -- All features
 TRUE, TRUE, TRUE, TRUE, TRUE,           -- All actions
 TRUE, TRUE, FALSE, FALSE);              -- User + billing management

-- Verify roles
SELECT role_id, role_name, 
       can_access_sentiment, can_access_dashboard, can_export
FROM `vantage-ai-prod.hr_insights.roles`
ORDER BY role_id;
```

#### Task 1.4: Create User Roles Table (Many-to-Many)

**Purpose:** Map users to their roles (supports multiple roles per user)

**SQL Script:**
```sql
-- Create user_roles junction table
CREATE TABLE `vantage-ai-prod.hr_insights.user_roles` (
    user_role_id STRING NOT NULL OPTIONS(description="UUID v4 unique identifier"),
    user_id STRING NOT NULL OPTIONS(description="FK to users table"),
    role_id STRING NOT NULL OPTIONS(description="FK to roles table"),
    
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="When role was assigned"),
    assigned_by STRING OPTIONS(description="User who assigned this role"),
    expires_at TIMESTAMP OPTIONS(description="Role expiration (optional)"),
    
    is_active BOOLEAN DEFAULT TRUE OPTIONS(description="Role assignment active status")
)
PARTITION BY DATE(assigned_at)
CLUSTER BY user_id, role_id
OPTIONS(
    description="User-Role assignments (many-to-many)",
    labels=[("security", "rbac")]
);

-- Assign roles to test users
INSERT INTO `vantage-ai-prod.hr_insights.user_roles` (
    user_role_id, user_id, role_id, assigned_by
)
SELECT 
    GENERATE_UUID(),
    u.user_id,
    CASE 
        WHEN u.user_type = 'owner' THEN 'role_owner'
        WHEN u.user_type = 'freelancer' THEN 'role_freelancer'
        WHEN u.user_type = 'organization' THEN 
            CASE 
                WHEN o.subscription_plan = 'basic' THEN 'role_basic'
                WHEN o.subscription_plan = 'gold' THEN 'role_gold'
                WHEN o.subscription_plan = 'premium' THEN 'role_premium'
            END
    END as role_id,
    'system' as assigned_by
FROM `vantage-ai-prod.hr_insights.users` u
LEFT JOIN `vantage-ai-prod.hr_insights.organizations` o 
    ON u.organization_id = o.organization_id;

-- Verify assignments
SELECT 
    u.email,
    u.user_type,
    r.role_name,
    ur.assigned_at
FROM `vantage-ai-prod.hr_insights.user_roles` ur
JOIN `vantage-ai-prod.hr_insights.users` u ON ur.user_id = u.user_id
JOIN `vantage-ai-prod.hr_insights.roles` r ON ur.role_id = r.role_id
ORDER BY ur.assigned_at DESC;
```

### Day 3: Session Management & Audit Logging

#### Task 1.5: Create User Sessions Table

**Purpose:** Track active user sessions and JWT tokens

**SQL Script:**
```sql
-- Create user_sessions table
CREATE TABLE `vantage-ai-prod.hr_insights.user_sessions` (
    -- Primary key
    session_id STRING NOT NULL OPTIONS(description="UUID v4 unique identifier"),
    user_id STRING NOT NULL OPTIONS(description="FK to users table"),
    
    -- Token management
    token_hash STRING NOT NULL OPTIONS(description="SHA256 hash of JWT access token"),
    refresh_token_hash STRING OPTIONS(description="SHA256 hash of refresh token"),
    
    -- Session metadata
    ip_address STRING OPTIONS(description="IP address of client"),
    user_agent STRING OPTIONS(description="Browser/client user agent"),
    device_type STRING OPTIONS(description="Device type: desktop, mobile, tablet"),
    location_country STRING OPTIONS(description="Country from IP geolocation"),
    location_city STRING OPTIONS(description="City from IP geolocation"),
    
    -- Expiration
    expires_at TIMESTAMP NOT NULL OPTIONS(description="Token expiration time"),
    last_activity_at TIMESTAMP OPTIONS(description="Last API call with this token"),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE OPTIONS(description="Session active status"),
    logout_at TIMESTAMP OPTIONS(description="When user logged out"),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Session creation time")
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, is_active
OPTIONS(
    description="User sessions and JWT token tracking",
    labels=[("security", "sessions")]
);

-- Create index for token lookup
-- Note: Use clustering for better query performance on token_hash
ALTER TABLE `vantage-ai-prod.hr_insights.user_sessions`
SET OPTIONS (
    clustering_fields="user_id, is_active, expires_at"
);

-- Verify creation
SELECT table_name, creation_time, row_count
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id = 'user_sessions';
```

#### Task 1.6: Create Audit Logs Table

**Purpose:** Track all security-related events for compliance and debugging

**SQL Script:**
```sql
-- Create audit_logs table
CREATE TABLE `vantage-ai-prod.hr_insights.audit_logs` (
    -- Primary key
    log_id STRING NOT NULL OPTIONS(description="UUID v4 unique identifier"),
    
    -- Actor
    user_id STRING OPTIONS(description="User who performed action"),
    organization_id STRING OPTIONS(description="Organization context"),
    
    -- Action details
    action STRING NOT NULL OPTIONS(description="Action: login, logout, create, update, delete, export, etc."),
    resource_type STRING OPTIONS(description="Resource: user, organization, job, document, etc."),
    resource_id STRING OPTIONS(description="ID of affected resource"),
    
    -- Request context
    ip_address STRING OPTIONS(description="IP address of request"),
    user_agent STRING OPTIONS(description="Browser/client user agent"),
    request_method STRING OPTIONS(description="HTTP method: GET, POST, PUT, DELETE"),
    request_path STRING OPTIONS(description="API endpoint path"),
    
    -- Result
    status STRING OPTIONS(description="Result: success, failure, denied"),
    error_message STRING OPTIONS(description="Error message if failed"),
    response_code INT64 OPTIONS(description="HTTP response code"),
    
    -- Additional data
    metadata JSON OPTIONS(description="Additional contextual data"),
    changes JSON OPTIONS(description="Before/after values for updates"),
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() OPTIONS(description="Event timestamp")
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, action, status
OPTIONS(
    description="Security and compliance audit trail",
    labels=[("security", "audit"), ("compliance", "true")]
);

-- Test audit log
INSERT INTO `vantage-ai-prod.hr_insights.audit_logs` (
    log_id, action, status, ip_address, created_at
) VALUES (
    GENERATE_UUID(),
    'schema_creation',
    'success',
    '127.0.0.1',
    CURRENT_TIMESTAMP()
);

-- Verify
SELECT log_id, action, status, created_at
FROM `vantage-ai-prod.hr_insights.audit_logs`
ORDER BY created_at DESC
LIMIT 10;
```

### Database Schema Validation

**Run these queries to verify all tables are created:**

```sql
-- List all security tables
SELECT 
    table_id,
    creation_time,
    row_count,
    size_bytes / 1024 / 1024 as size_mb,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), creation_time, DAY) as age_days
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id IN ('users', 'organizations', 'roles', 'user_roles', 'user_sessions', 'audit_logs')
ORDER BY table_id;

-- Check total storage
SELECT 
    SUM(size_bytes) / 1024 / 1024 as total_size_mb,
    COUNT(*) as table_count
FROM `vantage-ai-prod.hr_insights.__TABLES__`
WHERE table_id IN ('users', 'organizations', 'roles', 'user_roles', 'user_sessions', 'audit_logs');

-- Verify test data
SELECT 
    (SELECT COUNT(*) FROM `vantage-ai-prod.hr_insights.users`) as users_count,
    (SELECT COUNT(*) FROM `vantage-ai-prod.hr_insights.organizations`) as orgs_count,
    (SELECT COUNT(*) FROM `vantage-ai-prod.hr_insights.roles`) as roles_count,
    (SELECT COUNT(*) FROM `vantage-ai-prod.hr_insights.user_roles`) as user_roles_count;
```

**Expected Results:**
- ✅ 6 tables created
- ✅ 2 test users (owner, freelancer)
- ✅ 1 test organization
- ✅ 5 standard roles
- ✅ 2 user-role assignments
- ✅ Total size < 1 MB

---

## 🔐 Phase 2: Backend Authentication (Days 4-8)

### Overview
Implement JWT-based authentication in FastAPI with bcrypt password hashing, token generation, and user management endpoints.

### Day 4: Core Authentication Utilities

#### Task 2.1: Install Security Dependencies

**File:** `requirements.txt` (update)

```bash
# Add these lines to requirements.txt
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
slowapi==0.1.9
email-validator==2.1.0
```

**Run installation:**
```powershell
# Activate virtual environment first
.\pa_env\Scripts\Activate.ps1

# Install new dependencies
pip install python-jose[cryptography] passlib[bcrypt] python-multipart slowapi email-validator

# Verify installation
pip list | Select-String "jose|passlib|multipart|slowapi|email"

# Update requirements file
pip freeze > requirements.txt
```

#### Task 2.2: Create Security Configuration

**File:** `vantage_api/security_config.py` (create new)

```python
"""
Security Configuration
Centralized security settings for authentication and authorization
"""
import os
from datetime import timedelta
from typing import List

# ============================================================================
# JWT Configuration
# ============================================================================
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", 
    "CHANGE_THIS_IN_PRODUCTION_USE_LONG_RANDOM_STRING_12345678901234567890"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days

# ============================================================================
# Password Security
# ============================================================================
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
BCRYPT_ROUNDS = 12  # Cost factor for bcrypt (higher = more secure but slower)

# Special characters allowed in passwords
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}|;:,.<>?"

# ============================================================================
# Rate Limiting
# ============================================================================
RATE_LIMIT_PER_MINUTE = 60            # General API rate limit
RATE_LIMIT_AUTH_PER_MINUTE = 5        # Stricter for auth endpoints
RATE_LIMIT_REGISTER_PER_HOUR = 3      # Registration attempts per hour
RATE_LIMIT_PASSWORD_RESET_PER_HOUR = 3

# Rate limits by subscription tier (requests per minute)
RATE_LIMITS_BY_PLAN = {
    'freelancer': 30,
    'basic': 60,
    'gold': 120,
    'premium': 300,
    'owner': 10000,  # No practical limit
}

# ============================================================================
# Session Configuration
# ============================================================================
MAX_SESSIONS_PER_USER = 5  # Maximum concurrent sessions
SESSION_INACTIVITY_TIMEOUT = timedelta(hours=24)  # Auto-logout after inactivity
TOKEN_CLEANUP_INTERVAL_HOURS = 6  # How often to clean expired tokens

# ============================================================================
# Account Security
# ============================================================================
MAX_LOGIN_ATTEMPTS = 5           # Failed attempts before lockout
LOCKOUT_DURATION_MINUTES = 30    # Account lock duration
EMAIL_VERIFICATION_REQUIRED = True  # Require email verification
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# Password reset
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 15
PASSWORD_RESET_RATE_LIMIT_MINUTES = 60

# ============================================================================
# API Key Configuration (for organizations with Premium plan)
# ============================================================================
API_KEY_PREFIX = "vantage_"
API_KEY_LENGTH = 32  # Length of random part
API_KEY_HEADER = "X-API-Key"

# API rate limits by plan (requests per day)
API_RATE_LIMITS_BY_PLAN = {
    'premium': 10000,
    'owner': 100000,
}

# ============================================================================
# CORS Configuration
# ============================================================================
CORS_ALLOW_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
CORS_ALLOW_HEADERS = ["*"]

# ============================================================================
# Audit Logging
# ============================================================================
AUDIT_LOG_ACTIONS = [
    'login',
    'logout',
    'register',
    'password_change',
    'password_reset',
    'email_verify',
    'create',
    'update',
    'delete',
    'export',
    'api_call',
]

# ============================================================================
# Security Headers
# ============================================================================
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}

# ============================================================================
# Email Configuration (for verification emails)
# ============================================================================
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@vantage.ai")
EMAIL_FROM_NAME = "Vantage.AI"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ============================================================================
# Validation
# ============================================================================
def validate_config():
    """Validate security configuration on startup"""
    errors = []
    
    if len(SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")
    
    if "CHANGE_THIS" in SECRET_KEY:
        errors.append("JWT_SECRET_KEY must be changed in production")
    
    if BCRYPT_ROUNDS < 10:
        errors.append("BCRYPT_ROUNDS should be at least 10")
    
    if errors:
        raise ValueError(f"Security configuration errors: {', '.join(errors)}")

# Run validation on import
validate_config()
```

#### Task 2.3: Create Authentication Utilities

**File:** `vantage_api/utils/auth_utils.py` (create new)

```python
"""
Authentication Utilities
Functions for password hashing, JWT token generation, and validation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid
import secrets
import hashlib

import security_config

# ============================================================================
# Password Hashing
# ============================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password meets security requirements
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < security_config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {security_config.PASSWORD_MIN_LENGTH} characters"
    
    if security_config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if security_config.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if security_config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if security_config.PASSWORD_REQUIRE_SPECIAL:
        if not any(c in security_config.PASSWORD_SPECIAL_CHARS for c in password):
            return False, f"Password must contain at least one special character ({security_config.PASSWORD_SPECIAL_CHARS})"
    
    # Check for common weak passwords
    common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
    if password.lower() in common_passwords:
        return False, "Password is too common"
    
    return True, "Password is valid"

# ============================================================================
# JWT Token Management
# ============================================================================
def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token (user_id, email, etc.)
        expires_delta: Custom expiration time (optional)
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=security_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(uuid.uuid4())  # JWT ID for tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, security_config.SECRET_KEY, algorithm=security_config.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict) -> str:
    """
    Create JWT refresh token (longer expiration)
    
    Args:
        data: Data to encode in token
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=security_config.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    })
    
    encoded_jwt = jwt.encode(to_encode, security_config.SECRET_KEY, algorithm=security_config.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, security_config.SECRET_KEY, algorithms=[security_config.ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            return None
        
        # Check expiration (jwt.decode already does this, but double-check)
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None
        
        return payload
        
    except JWTError:
        return None
    except Exception:
        return None

def hash_token(token: str) -> str:
    """
    Create SHA256 hash of token for storage
    
    Args:
        token: JWT token string
        
    Returns:
        Hex string of token hash
    """
    return hashlib.sha256(token.encode()).hexdigest()

# ============================================================================
# API Key Management
# ============================================================================
def generate_api_key() -> str:
    """
    Generate organization API key
    
    Returns:
        API key string with prefix
    """
    random_part = secrets.token_urlsafe(security_config.API_KEY_LENGTH)
    return f"{security_config.API_KEY_PREFIX}{random_part}"

def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key string
        
    Returns:
        True if format is valid
    """
    if not api_key.startswith(security_config.API_KEY_PREFIX):
        return False
    
    if len(api_key) < len(security_config.API_KEY_PREFIX) + 20:
        return False
    
    return True

# ============================================================================
# Verification Tokens
# ============================================================================
def generate_verification_token() -> str:
    """
    Generate email verification token
    
    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(32)

def generate_password_reset_token() -> str:
    """
    Generate password reset token
    
    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(32)

# ============================================================================
# Utility Functions
# ============================================================================
def generate_user_id() -> str:
    """Generate UUID for new user"""
    return str(uuid.uuid4())

def generate_organization_id() -> str:
    """Generate UUID for new organization"""
    return str(uuid.uuid4())

def generate_session_id() -> str:
    """Generate UUID for new session"""
    return str(uuid.uuid4())

def get_token_expiry_time(minutes: int) -> datetime:
    """
    Get expiry timestamp for token
    
    Args:
        minutes: Minutes until expiry
        
    Returns:
        Expiry datetime
    """
    return datetime.utcnow() + timedelta(minutes=minutes)
```

### Day 5-6: Authentication Endpoints

#### Task 2.4: Create Authentication Schemas

**File:** `vantage_api/schemas/auth_models.py` (create new)

```python
"""
Authentication Models
Pydantic models for authentication request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================
class UserType(str, Enum):
    """User type enumeration"""
    OWNER = "owner"
    FREELANCER = "freelancer"
    ORGANIZATION = "organization"

class SubscriptionPlan(str, Enum):
    """Subscription plan enumeration"""
    BASIC = "basic"
    GOLD = "gold"
    PREMIUM = "premium"

class SubscriptionStatus(str, Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

# ============================================================================
# Request Models
# ============================================================================
class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    
    # User type
    user_type: UserType = Field(..., description="User type: freelancer or organization")
    
    # Organization-specific fields (required if user_type = organization)
    organization_name: Optional[str] = Field(None, description="Organization name")
    organization_type: Optional[str] = Field(None, description="Organization type")
    
    @validator('organization_name')
    def validate_org_name(cls, v, values):
        """Validate organization name is provided for organization users"""
        if values.get('user_type') == UserType.ORGANIZATION and not v:
            raise ValueError('organization_name is required for organization users')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "phone": "+1234567890",
                "user_type": "organization",
                "organization_name": "Acme Corp",
                "organization_type": "enterprise"
            }
        }

class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Refresh token")

class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr = Field(..., description="User email")

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")

# ============================================================================
# Response Models
# ============================================================================
class UserInfo(BaseModel):
    """User information"""
    user_id: str
    email: str
    full_name: str
    user_type: UserType
    organization_id: Optional[str] = None
    is_verified: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "user_type": "organization",
                "organization_id": "org-uuid",
                "is_verified": True
            }
        }

class OrganizationInfo(BaseModel):
    """Organization information"""
    organization_id: str
    organization_name: str
    subscription_plan: SubscriptionPlan
    subscription_status: SubscriptionStatus
    trial_end_date: Optional[datetime] = None
    max_users: int
    current_users: int
    
    class Config:
        schema_extra = {
            "example": {
                "organization_id": "org-uuid",
                "organization_name": "Acme Corp",
                "subscription_plan": "gold",
                "subscription_status": "active",
                "max_users": 20,
                "current_users": 5
            }
        }

class Permissions(BaseModel):
    """User permissions"""
    # Feature access
    can_access_linkedin: bool = False
    can_access_ats: bool = False
    can_access_journal: bool = False
    can_access_sentiment: bool = False
    can_access_dashboard: bool = False
    can_access_analytics: bool = False
    
    # Action permissions
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_export: bool = False
    
    # Admin permissions
    can_manage_users: bool = False
    can_manage_billing: bool = False
    can_view_audit_logs: bool = False
    can_manage_organizations: bool = False

class TokenResponse(BaseModel):
    """Login response with tokens"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until token expires")
    
    user: UserInfo
    organization: Optional[OrganizationInfo] = None
    permissions: Permissions
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "user_id": "uuid",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "user_type": "organization",
                    "is_verified": True
                },
                "permissions": {
                    "can_access_linkedin": True,
                    "can_access_ats": True
                }
            }
        }

class UserResponse(BaseModel):
    """User registration response"""
    user_id: str
    email: str
    full_name: str
    user_type: UserType
    is_active: bool
    is_verified: bool
    message: str = Field(default="Registration successful")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "uuid",
                "email": "user@example.com",
                "full_name": "John Doe",
                "user_type": "organization",
                "is_active": True,
                "is_verified": False,
                "message": "Registration successful. Please check your email."
            }
        }

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }
```

*[Document continues with Days 6-18 implementation details...]*

**Note:** This is Part 1 of the implementation plan. The complete document is ~15,000 lines covering all phases, code templates, testing procedures, and deployment steps. Would you like me to:

1. Continue with the remaining sections?
2. Create separate focused documents for each phase?
3. Start with a summary document and detailed phase-specific guides?

Let me know how you'd like to proceed!