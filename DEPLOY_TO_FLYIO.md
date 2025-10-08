# Deploy to Fly.io - Step-by-Step Guide

**Date**: 2025-10-08
**App Name**: tuhs-abx-steward
**Region**: ewr (US East)

---

## Prerequisites

1. ✅ Fly.io CLI installed (`flyctl` or `fly`)
2. ✅ Logged into Fly.io account
3. ✅ Git repository clean (all changes committed)
4. ✅ All changes tested locally

---

## Pre-Deployment Checklist

### 1. Test Locally First
```bash
# Start local server
python fastapi_server.py

# Test in browser
open http://localhost:8080

# Verify error reporting works
# 1. Generate a recommendation
# 2. Click "Flag Error"
# 3. Submit error report
# 4. Check logs/error_reports/ for saved file
```

### 2. Commit All Changes
```bash
# Check git status
git status

# Add all files
git add .

# Commit with descriptive message
git commit -m "Add error reporting system - Phase 1 complete

- Add 3 new API endpoints for error reporting
- Add error report modal to Alpine.js frontend
- Add JSONL storage for error reports
- Add validation and status workflow
- Update documentation"

# Push to remote (optional but recommended)
git push origin main
```

### 3. Check Required Files
```bash
# Verify all required files exist
ls -la fly.toml Dockerfile alpine_frontend.html fastapi_server.py
```

**Expected Output**: All files should be present ✅

---

## Deployment Steps

### Step 1: Verify Fly.io Login
```bash
fly auth whoami
```

**Expected Output**:
```
Email: your-email@example.com
Logged in!
```

If not logged in:
```bash
fly auth login
```

---

### Step 2: Check Current Deployment Status
```bash
fly status --app tuhs-abx-steward
```

**Expected Output**: Shows current app status, machines, etc.

---

### Step 3: Set Environment Variables (If Not Already Set)

The app requires `OPENROUTER_API_KEY`. Check if it's set:

```bash
fly secrets list --app tuhs-abx-steward
```

If not set, add it:
```bash
fly secrets set OPENROUTER_API_KEY="your-api-key-here" --app tuhs-abx-steward
```

**Important**: Replace `your-api-key-here` with your actual API key!

---

### Step 4: Deploy to Fly.io

**Option A: Simple Deploy (Recommended)**
```bash
fly deploy --app tuhs-abx-steward
```

**Option B: Deploy with Build Logs**
```bash
fly deploy --app tuhs-abx-steward --verbose
```

**Option C: Deploy Specific Dockerfile**
```bash
fly deploy --app tuhs-abx-steward --dockerfile Dockerfile
```

### Expected Output:
```
==> Verifying app config
--> Verified app config
==> Building image
--> Building image with Docker
...
--> Pushing image to fly
...
==> Deploying tuhs-abx-steward
--> Machine ... updating
--> Machine ... updated
==> Monitoring deployment
...
--> Deployment successful!
```

**Deployment Time**: Typically 2-5 minutes

---

### Step 5: Verify Deployment

#### Check App Status
```bash
fly status --app tuhs-abx-steward
```

**Look for**:
- ✅ Status: running
- ✅ Health Checks: passing

#### Check Logs
```bash
fly logs --app tuhs-abx-steward
```

**Look for**:
```
🚀 TUHS Antibiotic Steward - FastAPI Server
==================================================
📡 API Docs:     /api/docs
🌐 Frontend:     /
❤️  Health:      /health
📝 Error Reports: /api/error-reports
==================================================
INFO:     Uvicorn running on http://0.0.0.0:8080
```

#### Test Health Endpoint
```bash
fly ssh console --app tuhs-abx-steward -C "curl http://localhost:8080/health"
```

**Expected**:
```json
{"status":"healthy","backend":"FastAPI","version":"2.0.0","timestamp":"..."}
```

---

### Step 6: Test in Browser

#### Get App URL
```bash
fly info --app tuhs-abx-steward
```

**Look for**: Hostname (e.g., `tuhs-abx-steward.fly.dev`)

#### Open in Browser
```bash
fly open --app tuhs-abx-steward
```

Or manually visit: `https://tuhs-abx-steward.fly.dev`

---

### Step 7: Test Error Reporting on Production

1. **Generate Recommendation**
   - Fill patient data form
   - Click "Generate Recommendation"
   - Verify recommendation displays

2. **Test Error Reporting**
   - Click "Flag Error" button
   - Fill error report form
   - Click "Submit Error Report"
   - Verify success message with Error ID

3. **Check Backend (Via SSH)**
```bash
fly ssh console --app tuhs-abx-steward

# Once in SSH session:
ls -la logs/error_reports/
cat logs/error_reports/$(date +%Y-%m-%d).jsonl
exit
```

---

## Troubleshooting

### Issue: Deployment Fails

**Check build logs**:
```bash
fly logs --app tuhs-abx-steward
```

**Common causes**:
1. Missing files in Dockerfile
2. Python dependency issues
3. Port mismatch (should be 8080)

**Solution**: Check Dockerfile COPY commands match your file structure

---

### Issue: App Won't Start

**Check logs**:
```bash
fly logs --app tuhs-abx-steward --recent
```

**Common causes**:
1. OPENROUTER_API_KEY not set
2. Import errors (missing Python packages)
3. Port binding issues

**Solution**:
```bash
# Check secrets
fly secrets list --app tuhs-abx-steward

# Restart app
fly restart --app tuhs-abx-steward
```

---

### Issue: Error Reporting Not Working

**Check if logs directory exists**:
```bash
fly ssh console --app tuhs-abx-steward -C "ls -la logs/"
```

**If missing**:
```bash
fly ssh console --app tuhs-abx-steward -C "mkdir -p logs/error_reports"
```

**Note**: Directory should be created automatically by fastapi_server.py

---

### Issue: 404 on Frontend

**Check alpine_frontend.html is copied**:
```bash
fly ssh console --app tuhs-abx-steward -C "ls -la alpine_frontend.html"
```

**If missing**: Update Dockerfile to include it (already included in line 25)

---

### Issue: Health Check Failing

**Test health endpoint manually**:
```bash
fly ssh console --app tuhs-abx-steward -C "curl http://localhost:8080/health"
```

**If it works**: Health check will pass soon (30s interval)

**If it fails**: Check logs for startup errors

---

## Rollback (If Needed)

If the new deployment has issues:

### Option 1: Quick Rollback
```bash
fly releases --app tuhs-abx-steward
fly rollback --app tuhs-abx-steward
```

### Option 2: Deploy Previous Version
```bash
# Check git history
git log --oneline

# Checkout previous commit
git checkout <previous-commit-hash>

# Deploy
fly deploy --app tuhs-abx-steward

# Return to latest
git checkout main
```

---

## Post-Deployment Verification

### 1. Test All Features
- [ ] Home page loads
- [ ] Can generate recommendation
- [ ] "Flag Error" button appears
- [ ] Error report modal opens
- [ ] Can submit error report
- [ ] Success message appears
- [ ] Error saved to backend

### 2. Check API Endpoints
```bash
# Health check
curl https://tuhs-abx-steward.fly.dev/health

# API docs
open https://tuhs-abx-steward.fly.dev/api/docs

# Error reports (admin only)
curl https://tuhs-abx-steward.fly.dev/api/error-reports
```

### 3. Monitor Logs
```bash
# Watch logs in real-time
fly logs --app tuhs-abx-steward -f
```

**Look for**:
- ✅ No errors
- ✅ Successful health checks
- ✅ API requests completing

---

## Scaling (Optional)

### Increase Memory (If Needed)
```bash
fly scale memory 2048 --app tuhs-abx-steward
```

### Increase CPU (If Needed)
```bash
fly scale vm shared-cpu-2x --app tuhs-abx-steward
```

### Keep Always Running (Instead of Auto-Stop)
Edit `fly.toml`:
```toml
[http_service]
  auto_stop_machines = false
  min_machines_running = 1
```

Then redeploy:
```bash
fly deploy --app tuhs-abx-steward
```

---

## Monitoring

### View Metrics
```bash
fly dashboard --app tuhs-abx-steward
```

### Watch Logs Live
```bash
fly logs --app tuhs-abx-steward -f
```

### Check Machine Status
```bash
fly machine list --app tuhs-abx-steward
```

---

## Quick Reference

### Common Commands
```bash
# Deploy
fly deploy --app tuhs-abx-steward

# Check status
fly status --app tuhs-abx-steward

# View logs
fly logs --app tuhs-abx-steward

# Open app
fly open --app tuhs-abx-steward

# SSH into machine
fly ssh console --app tuhs-abx-steward

# Restart app
fly restart --app tuhs-abx-steward

# Check secrets
fly secrets list --app tuhs-abx-steward

# View releases
fly releases --app tuhs-abx-steward
```

---

## Error Report Storage Note

⚠️ **Important**: Fly.io uses ephemeral storage. Error reports saved to `logs/error_reports/` will be lost when machines restart.

**Solutions for Production**:

### Option 1: Use Fly.io Volumes (Persistent Storage)
```bash
# Create volume
fly volumes create error_reports --size 1 --app tuhs-abx-steward

# Update fly.toml
# Add under [mounts]
# source = "error_reports"
# destination = "/app/logs/error_reports"

# Redeploy
fly deploy --app tuhs-abx-steward
```

### Option 2: Use External Database
- Store error reports in PostgreSQL instead of JSONL
- Add `psycopg2-binary` to requirements
- Update `fastapi_server.py` to use database

### Option 3: Use S3/Cloud Storage
- Store error reports in AWS S3 or similar
- Add `boto3` to requirements
- Update `fastapi_server.py` to write to S3

**For now (testing)**: Current setup works fine, reports saved during session

---

## Success Criteria

✅ Deployment completes without errors
✅ App status shows "running"
✅ Health checks passing
✅ Frontend loads in browser
✅ Can generate recommendations
✅ Error reporting button visible
✅ Error reports can be submitted
✅ No errors in logs

---

## Next Steps After Deployment

1. **Test with pilot users**
   - Share Fly.io URL with pharmacists
   - Collect error reports
   - Monitor logs for issues

2. **Implement Phase 2**
   - Automated verification script
   - Download error reports periodically
   - Generate test cases

3. **Set up monitoring**
   - Fly.io metrics dashboard
   - Email alerts for critical errors
   - Log aggregation (optional)

---

**Deployment Status**: Ready to deploy
**Estimated Time**: 5-10 minutes
**Command**: `fly deploy --app tuhs-abx-steward`
