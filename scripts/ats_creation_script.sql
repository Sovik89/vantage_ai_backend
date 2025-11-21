-- ==================== ATS Tables Schema ====================
-- Privacy-Compliant: NO PII storage, only aggregated analytics
-- Run these in BigQuery Console or use the Python script below

-- ==================== Table 1: ats_jobs ====================
-- Stores job metadata only (NO candidate PII)

CREATE TABLE IF NOT EXISTS `your-project-id.your-dataset.ats_jobs` (
  job_id STRING NOT NULL,
  position_title STRING,
  organization STRING,
  user_email STRING,  -- Client user only (not candidates)
  total_candidates_analyzed INT64,
  status STRING,  -- PENDING, PROCESSING, COMPLETED, FAILED
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  completed_at TIMESTAMP,
  record_date DATE,
  record_date_str STRING,
  report_url STRING,
  error_message STRING,
  meta STRING  -- JSON string for flexible metadata
)
OPTIONS(
  description="ATS job metadata - tracks analysis jobs"
);

-- ==================== Table 2: ats_results ====================
-- Stores AGGREGATED results only (NO individual candidate data)

CREATE TABLE IF NOT EXISTS `your-project-id.your-dataset.ats_results` (
  result_id STRING NOT NULL,
  job_id STRING,
  created_at TIMESTAMP,
  record_date DATE,
  record_date_str STRING,
  
  -- Aggregated Statistics (NO INDIVIDUAL DATA)
  total_candidates INT64,
  avg_match_percentage FLOAT64,
  median_match_percentage FLOAT64,
  max_match_percentage FLOAT64,
  min_match_percentage FLOAT64,
  
  -- Match Distribution
  high_match_count INT64,  -- >= 70%
  medium_match_count INT64,  -- 50-69%
  low_match_count INT64,  -- < 50%
  
  -- Skills Analysis (Aggregated across all candidates)
  avg_skills_match FLOAT64,
  most_common_missing_skills ARRAY<STRING>,
  most_common_found_skills ARRAY<STRING>,
  
  -- Experience Analysis (Aggregated)
  avg_experience_match FLOAT64,
  avg_candidate_experience_years FLOAT64,
  
  -- AI Detection Summary (Aggregated)
  ai_generated_detected_count INT64,
  avg_ai_probability FLOAT64,
  high_ai_risk_count INT64,
  
  -- Technical & Domain (Aggregated)
  avg_technical_depth FLOAT64,
  avg_domain_relevance FLOAT64,
  
  -- Bias Detection Summary
  total_bias_flags INT64,
  bias_types_detected ARRAY<STRING>,
  
  -- Key Insights (Anonymized Patterns)
  common_strengths ARRAY<STRING>,
  common_gaps ARRAY<STRING>,
  key_recommendations ARRAY<STRING>,
  
  -- Summary
  analysis_summary STRING,
  meta STRING  -- JSON string for flexible metadata
)
OPTIONS(
  description="ATS aggregated results - NO PII, only statistics and patterns"
);

-- ==================== Indexes for Performance ====================

-- Index on job_id for quick lookups
CREATE INDEX IF NOT EXISTS idx_ats_jobs_job_id
ON `your-project-id.your-dataset.ats_jobs`(job_id);

CREATE INDEX IF NOT EXISTS idx_ats_results_job_id
ON `your-project-id.your-dataset.ats_results`(job_id);

-- Index on created_at for time-series queries
CREATE INDEX IF NOT EXISTS idx_ats_jobs_created_at
ON `your-project-id.your-dataset.ats_jobs`(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ats_results_created_at
ON `your-project-id.your-dataset.ats_results`(created_at DESC);

-- ==================== Sample Queries ====================

-- Get job with aggregated results
SELECT 
  j.job_id,
  j.position_title,
  j.organization,
  j.total_candidates_analyzed,
  j.status,
  j.created_at,
  r.avg_match_percentage,
  r.high_match_count,
  r.ai_generated_detected_count,
  r.most_common_missing_skills
FROM `your-project-id.your-dataset.ats_jobs` j
LEFT JOIN `your-project-id.your-dataset.ats_results` r
  ON j.job_id = r.job_id
WHERE j.job_id = 'YOUR_JOB_ID'
LIMIT 1;

-- Get recent analyses
SELECT 
  job_id,
  position_title,
  total_candidates_analyzed,
  status,
  created_at
FROM `your-project-id.your-dataset.ats_jobs`
ORDER BY created_at DESC
LIMIT 10;

-- Get aggregated insights by domain
SELECT 
  j.organization,
  COUNT(*) as total_jobs,
  AVG(r.avg_match_percentage) as avg_match_across_jobs,
  AVG(r.ai_generated_detected_count) as avg_ai_detected
FROM `your-project-id.your-dataset.ats_jobs` j
JOIN `your-project-id.your-dataset.ats_results` r
  ON j.job_id = r.job_id
GROUP BY j.organization
ORDER BY total_jobs DESC;