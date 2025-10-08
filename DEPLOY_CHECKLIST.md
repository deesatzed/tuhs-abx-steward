# Fly.io Deployment Checklist

**Quick reference for deploying to Fly.io**

---

## Pre-Deployment (Do This First)

```bash
# 1. Test locally
python fastapi_server.py
# Open http://localhost:8080 and test error reporting

# 2. Commit changes
git status
git add .
git commit -m "Add error reporting system - Phase 1"
git push origin main

# 3. Verify files
ls -la fly.toml Dockerfile alpine_frontend.html fastapi_server.py
```

---

## Deploy Command

```bash
fly deploy --app tuhs-abx-steward
```

**That's it!** Wait 2-5 minutes for deployment.

---

## Verify Deployment

```bash
# Check status
fly status --app tuhs-abx-steward

# Check logs
fly logs --app tuhs-abx-steward

# Open in browser
fly open --app tuhs-abx-steward
```

---

## Test Error Reporting

1. Visit: https://tuhs-abx-steward.fly.dev
2. Generate a recommendation
3. Click "Flag Error"
4. Submit error report
5. Verify success message

---

## If Something Goes Wrong

```bash
# View recent logs
fly logs --app tuhs-abx-steward --recent

# Restart app
fly restart --app tuhs-abx-steward

# Rollback to previous version
fly releases --app tuhs-abx-steward
fly rollback --app tuhs-abx-steward
```

---

## Important Notes

⚠️ **Error Reports Storage**
- Error reports saved to `/app/logs/error_reports/`
- Storage is ephemeral (lost on restart)
- For production: Set up Fly.io volumes or external storage
- See DEPLOY_TO_FLYIO.md for persistent storage options

✅ **What's Included in Deployment**
- FastAPI backend with error reporting endpoints
- Alpine.js frontend with error report modal
- Updated alpine_frontend.html
- All new API endpoints

---

## Quick Commands

```bash
# Deploy
fly deploy --app tuhs-abx-steward

# Status
fly status --app tuhs-abx-steward

# Logs
fly logs --app tuhs-abx-steward -f

# Open app
fly open --app tuhs-abx-steward

# SSH
fly ssh console --app tuhs-abx-steward
```

---

**For detailed instructions, see: DEPLOY_TO_FLYIO.md**
