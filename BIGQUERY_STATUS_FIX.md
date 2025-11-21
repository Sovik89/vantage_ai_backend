# BigQuery Status Update Fix - LinkedIn Scout

## Problem

BigQuery streaming buffer prevents UPDATE/DELETE operations immediately after INSERT:
```
Error: UPDATE or DELETE would affect rows in the streaming buffer
```

## Solution

**Changed from UPDATE to INSERT pattern**: Instead of updating existing rows, we now insert a new row with the same `job_id` and updated status.

---

## Changes Made

### 1. **Completed Status** (Success Path)

**Before** (UPDATE):
```sql
UPDATE linkedin_jobs
SET status = 'completed', total_found = 10, ...
WHERE job_id = 'xxx'
```

**After** (INSERT):
```python
# Fetch original job data
query = "SELECT * FROM linkedin_jobs WHERE job_id = 'xxx' LIMIT 1"

# Insert new row with completed status
completed_job_row = {
    "job_id": job_id,  # Same job_id
    "status": "completed",
    "created_at": original_job.get('created_at'),  # Preserve original
    "updated_at": completed_at,  # New timestamp
    "completed_at": completed_at,
    "total_found": 10,
    "total_analyzed": 10,
    ... all other fields from original ...
}

bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [completed_job_row])
```

### 2. **Failed Status** (Error Path)

Same pattern for failed jobs:
```python
failed_job_row = {
    "job_id": job_id,  # Same job_id
    "status": "failed",
    "summary_text": f"Job failed: {error_message}",
    ... all other fields from original ...
}

bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [failed_job_row])
```

### 3. **No Candidates Found** (Empty Results)

Same pattern when no candidates are found:
```python
completed_job_row = {
    "job_id": job_id,  # Same job_id
    "status": "completed",
    "total_found": 0,
    "total_analyzed": 0,
    "summary_text": "No candidates found matching criteria",
    ... all other fields from original ...
}

bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [completed_job_row])
```

### 4. **Get Job Status** (Retrieval)

Updated query to fetch **latest** status row:

**Before**:
```sql
SELECT * FROM linkedin_jobs
WHERE job_id = 'xxx'
LIMIT 1
```

**After**:
```sql
SELECT * FROM linkedin_jobs
WHERE job_id = 'xxx'
ORDER BY updated_at DESC  -- Fetch latest row
LIMIT 1
```

---

## How It Works

### BigQuery Table Structure

The `linkedin_jobs` table now contains **multiple rows** per job_id:

| job_id | status | created_at | updated_at | total_found |
|--------|--------|------------|------------|-------------|
| abc123 | processing | 2025-11-15 10:00:00 | 2025-11-15 10:00:00 | 0 |
| abc123 | completed | 2025-11-15 10:00:00 | 2025-11-15 10:02:30 | 10 |

- **First row**: Initial job creation (`status = 'processing'`)
- **Second row**: Job completion (`status = 'completed'`)
- Same `job_id`, different `status` and `updated_at`

### Fetching Latest Status

Always use `ORDER BY updated_at DESC LIMIT 1` to get the most recent status:

```sql
SELECT * FROM linkedin_jobs
WHERE job_id = 'abc123'
ORDER BY updated_at DESC
LIMIT 1
```

Returns: `status = 'completed'` (latest row)

---

## Benefits

### ✅ No More Streaming Buffer Errors

- INSERT operations work immediately
- No 90-second wait period needed
- No UPDATE/DELETE errors

### ✅ Audit Trail

- Complete history of job status changes
- Can track when job started, completed, or failed
- Useful for debugging and analytics

### ✅ BigQuery Best Practice

- Streaming buffer designed for INSERT, not UPDATE
- Follows append-only pattern
- Better performance for analytics queries

---

## Code Locations

### Files Modified

- **`routers/linkedin_scout.py`**
  - Line ~532: Success path - insert completed status
  - Line ~430: No results path - insert completed status  
  - Line ~600: Error path - insert failed status
  - Line ~803: Get job - ORDER BY updated_at DESC

---

## Testing

### Test Completed Status

1. Start LinkedIn Scout job
2. Wait for completion
3. Check BigQuery:
   ```sql
   SELECT * FROM hr_insights.linkedin_jobs
   WHERE job_id = 'your_job_id'
   ORDER BY updated_at DESC
   ```
4. **Expected**: 2 rows
   - Row 1 (latest): `status = 'completed'`
   - Row 2 (oldest): `status = 'processing'`

### Test Failed Status

1. Trigger job failure (invalid JD or network error)
2. Check BigQuery:
   ```sql
   SELECT * FROM hr_insights.linkedin_jobs
   WHERE job_id = 'failed_job_id'
   ORDER BY updated_at DESC
   ```
3. **Expected**: 2 rows
   - Row 1: `status = 'failed'`
   - Row 2: `status = 'processing'`

### Test API Response

```bash
GET /api/linkedin/jobs/{job_id}
```

**Expected Response**:
```json
{
  "job_id": "abc123",
  "status": "completed",  // Latest status
  "total_candidates": 10,
  "completed_at": "2025-11-15T10:02:30Z",
  ...
}
```

---

## Migration Notes

### Existing Jobs

For jobs already in the table with single rows:
- No migration needed
- New status updates will create additional rows
- Old queries still work (just fetch first/last row)

### Frontend Compatibility

No frontend changes needed:
- API still returns single job object
- `status` field shows latest status
- Response structure unchanged

---

## Alternative Approaches (Not Used)

### ❌ Option 1: Wait 90 seconds before UPDATE
- **Con**: Terrible user experience
- **Con**: Job shows "processing" for 90+ seconds after completion

### ❌ Option 2: Use MERGE statement
- **Con**: Still fails on streaming buffer
- **Con**: More complex syntax

### ❌ Option 3: Staging table pattern
- **Con**: Requires additional table
- **Con**: More complex pipeline
- **Pro**: Could batch updates hourly

### ✅ Option 4: INSERT pattern (CHOSEN)
- **Pro**: Works immediately
- **Pro**: Simple implementation
- **Pro**: Provides audit trail
- **Pro**: BigQuery best practice

---

## Summary

✅ **Changed**: UPDATE → INSERT pattern for status changes  
✅ **Result**: No more streaming buffer errors  
✅ **Pattern**: Multiple rows per job_id, fetch latest by `updated_at DESC`  
✅ **Benefit**: Immediate status updates + complete audit trail  

**Status**: ✅ Fully implemented and ready for testing
