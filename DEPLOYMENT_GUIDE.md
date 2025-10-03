# Production Deployment Guide

**System**: TUHS Antibiotic Recommendation System v2.0  
**Architecture**: Agno Agent + OpenRouter + PostgreSQL/pgvector  
**Status**: Production Ready  

---

## Pre-Deployment Checklist

### Infrastructure Requirements

- [ ] **Server**: Linux/macOS with Node.js 20+ installed
- [ ] **Database**: PostgreSQL 15+ with pgvector extension
- [ ] **Memory**: Minimum 4GB RAM (8GB recommended)
- [ ] **Storage**: 10GB for application + database
- [ ] **Network**: HTTPS access to OpenRouter API (openrouter.ai)

### API Keys & Credentials

- [ ] OpenRouter API key obtained from https://openrouter.ai/settings/keys
- [ ] Database credentials and connection string prepared
- [ ] Backup/recovery credentials documented

---

## Step 1: Server Setup

### Install Node.js

```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# Verify
node --version  # Should show v20.x.x
npm --version   # Should show v10.x.x
```

### Install PostgreSQL + pgvector

```bash
# macOS
brew install postgresql@15 pgvector
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-15-pgvector
sudo systemctl start postgresql

# Verify pgvector
psql -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

---

## Step 2: Database Initialization

### Create Database

```bash
# Create database
createdb antibiotic_db

# Or via psql
psql -U postgres -c "CREATE DATABASE antibiotic_db;"

# Create user (if needed)
psql -U postgres -c "CREATE USER abx_user WITH PASSWORD 'secure_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE antibiotic_db TO abx_user;"
```

### Test Connection

```bash
psql -d antibiotic_db -c "SELECT version();"
```

---

## Step 3: Application Deployment

### Clone/Copy Application

```bash
# Copy phase2 directory to server
cd /opt  # Or your preferred location
cp -r /path/to/phase2 ./tuhs-abx-v2

cd tuhs-abx-v2
```

### Install Dependencies

```bash
npm install --production

# Verify installation
npm list --depth=0
```

### Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with production values
nano .env
```

**Required `.env` values**:
```bash
NODE_ENV=production
PORT=3000

OPENROUTER_API_KEY=sk-or-v1-xxx  # Your actual key
OPENROUTER_SITE_URL=https://abx.tuhs.edu
OPENROUTER_SITE_NAME=TUHS Antibiotic Steward

DATABASE_URL=postgresql://abx_user:secure_password@localhost:5432/antibiotic_db

DEFAULT_MODEL=openai/gpt-4o
FALLBACK_MODEL=openai/gpt-4o-mini
ICU_MODEL=anthropic/claude-3.7-sonnet
```

---

## Step 4: Database Schema Setup

```bash
# Initialize database schema
npm run setup:db

# Expected output:
# ✅ Database connection successful
# ✅ Database schema created successfully
```

### Verify Schema

```bash
psql -d antibiotic_db -c "\dt"

# Should show:
#  Schema |         Name          | Type  |  Owner
# --------+-----------------------+-------+---------
#  public | antibiotic_guidelines | table | abx_user
```

---

## Step 5: Load Knowledge Base

```bash
# Load TUHS guidelines
npm run load:knowledge

# Expected output:
# 📖 Reading ABXguideInp.json...
# ✅ Created 180 guideline chunks
# 🧠 Generating embeddings...
# 💾 Inserting chunks into database...
# ✅ Knowledge base loaded successfully!
```

**This takes 5-10 minutes** depending on OpenRouter API speed.

### Verify Knowledge Base

```bash
psql -d antibiotic_db -c "SELECT COUNT(*) FROM antibiotic_guidelines;"

# Should show ~180 rows
```

---

## Step 6: Test Application

### Start Server (Test Mode)

```bash
npm start

# Expected output:
# 🚀 Server running on http://localhost:3000
# 📊 Health check: http://localhost:3000/api/health
# 🏥 Using OpenRouter for LLM access
```

### Health Check

```bash
curl http://localhost:3000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "database": "connected",
#   "llm_provider": "openrouter",
#   "timestamp": "2025-10-01T..."
# }
```

### Test Recommendation

```bash
curl -X POST http://localhost:3000/api/recommendation/sync \
  -H "Content-Type: application/json" \
  -d '{
    "age": "65",
    "weight_kg": "70",
    "gfr": "60",
    "acuity": "Ward",
    "source_category": "Pneumonia",
    "allergies": "None",
    "culture_results": "Pending",
    "prior_resistance": "None"
  }'

# Should return markdown recommendation within 5 seconds
```

---

## Step 7: Process Manager Setup (Production)

### Install PM2

```bash
npm install -g pm2
```

### Create PM2 Ecosystem File

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'tuhs-abx-v2',
    script: './server.js',
    instances: 2,  // Or 'max' for all CPU cores
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s'
  }]
};
```

### Start with PM2

```bash
pm2 start ecosystem.config.js

# Verify
pm2 status

# View logs
pm2 logs tuhs-abx-v2

# Monitor
pm2 monit
```

### Setup PM2 Startup

```bash
# Generate startup script
pm2 startup

# Save current process list
pm2 save
```

---

## Step 8: Reverse Proxy (Nginx)

### Install Nginx

```bash
# Ubuntu/Debian
sudo apt-get install nginx

# macOS
brew install nginx
```

### Configure Nginx

Create `/etc/nginx/sites-available/tuhs-abx`:

```nginx
upstream tuhs_abx_backend {
    least_conn;
    server localhost:3000;
    # Add more instances if using PM2 cluster mode:
    # server localhost:3001;
    keepalive 64;
}

server {
    listen 80;
    server_name abx.tuhs.edu;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name abx.tuhs.edu;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/tuhs-abx.crt;
    ssl_certificate_key /etc/ssl/private/tuhs-abx.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/tuhs-abx-access.log;
    error_log /var/log/nginx/tuhs-abx-error.log;

    # Static files
    location /public {
        alias /opt/tuhs-abx-v2/public;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints (streaming support)
    location /api {
        proxy_pass http://tuhs_abx_backend;
        proxy_http_version 1.1;
        
        # WebSocket/SSE support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts (for streaming)
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Disable buffering for SSE
        proxy_buffering off;
        proxy_cache off;
    }

    # Root
    location / {
        proxy_pass http://tuhs_abx_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/tuhs-abx /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

---

## Step 9: SSL Certificate Setup

### Option A: Let's Encrypt (Free)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d abx.tuhs.edu
```

### Option B: Internal CA Certificate

```bash
# Place certificate files
sudo cp tuhs-abx.crt /etc/ssl/certs/
sudo cp tuhs-abx.key /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/tuhs-abx.key
```

---

## Step 10: Monitoring & Logging

### Log Rotation

Create `/etc/logrotate.d/tuhs-abx`:

```
/opt/tuhs-abx-v2/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 node node
    sharedscripts
    postrotate
        pm2 reloadLogs
    endscript
}
```

### Health Check Monitoring

Create cron job for health checks:

```bash
crontab -e

# Add:
*/5 * * * * curl -f http://localhost:3000/api/health || echo "Health check failed" | mail -s "TUHS ABX Alert" admin@tuhs.edu
```

### Application Monitoring

```bash
# Install PM2 monitoring (optional)
pm2 install pm2-logrotate

# View metrics
pm2 monit
```

---

## Step 11: Backup Strategy

### Database Backup

Create `/opt/tuhs-abx-v2/scripts/backup-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/tuhs-abx"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump antibiotic_db | gzip > $BACKUP_DIR/antibiotic_db_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make executable and schedule:

```bash
chmod +x /opt/tuhs-abx-v2/scripts/backup-db.sh

# Add to crontab
0 2 * * * /opt/tuhs-abx-v2/scripts/backup-db.sh
```

---

## Step 12: Security Hardening

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Block direct access to app port
sudo ufw deny 3000/tcp
```

### File Permissions

```bash
cd /opt/tuhs-abx-v2

# Secure .env file
chmod 600 .env

# Set ownership
sudo chown -R node:node /opt/tuhs-abx-v2

# Protect logs directory
chmod 750 logs/
```

### Database Security

```bash
# Disable remote database access (if on same server)
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Change to:
# host    antibiotic_db    abx_user    127.0.0.1/32    md5
```

---

## Step 13: Performance Tuning

### PostgreSQL Configuration

Edit `/etc/postgresql/15/main/postgresql.conf`:

```
# Memory
shared_buffers = 256MB
effective_cache_size = 1GB

# Connections
max_connections = 100

# Performance
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# Maintenance
maintenance_work_mem = 64MB
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Node.js Optimization

In `ecosystem.config.js`:

```javascript
env: {
  NODE_ENV: 'production',
  NODE_OPTIONS: '--max-old-space-size=2048',  // 2GB heap
  UV_THREADPOOL_SIZE: 16  // For async operations
}
```

---

## Step 14: Post-Deployment Testing

### Functional Tests

```bash
# 1. Health check
curl https://abx.tuhs.edu/api/health

# 2. Simple recommendation
curl -X POST https://abx.tuhs.edu/api/recommendation/sync \
  -H "Content-Type: application/json" \
  -d '{"age":"65","acuity":"Ward","source_category":"Pneumonia"}'

# 3. Complex case (ICU + allergies)
curl -X POST https://abx.tuhs.edu/api/recommendation/sync \
  -H "Content-Type: application/json" \
  -d '{"age":"70","acuity":"ICU","source_category":"Pneumonia","allergies":"Penicillin (anaphylaxis)","prior_resistance":"MRSA"}'
```

### Performance Tests

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -p test-payload.json -T application/json https://abx.tuhs.edu/api/recommendation/sync

# Analyze results:
# - Response time p50, p95, p99
# - Requests per second
# - Failed requests
```

### Stress Test

```bash
# Monitor during stress test
pm2 monit

# Database connections
psql -d antibiotic_db -c "SELECT count(*) FROM pg_stat_activity WHERE datname='antibiotic_db';"

# System resources
htop
```

---

## Step 15: Documentation & Handoff

### Create Operations Runbook

Document in `/opt/tuhs-abx-v2/RUNBOOK.md`:

1. **Common Issues**:
   - Database connection errors → Check PostgreSQL status
   - OpenRouter API errors → Verify API key, check rate limits
   - Slow responses → Check database query performance

2. **Restart Procedures**:
   ```bash
   pm2 restart tuhs-abx-v2
   sudo systemctl restart postgresql
   sudo systemctl reload nginx
   ```

3. **Log Locations**:
   - Application: `/opt/tuhs-abx-v2/logs/audit-*.log`
   - PM2: `/opt/tuhs-abx-v2/logs/pm2-*.log`
   - Nginx: `/var/log/nginx/tuhs-abx-*.log`

4. **Emergency Contacts**:
   - Development Team: dev@tuhs.edu
   - Database Admin: dba@tuhs.edu
   - On-Call: +1-xxx-xxx-xxxx

### Training Materials

- User guide for clinical staff
- Video walkthrough of interface
- FAQ document
- Troubleshooting guide

---

## Rollback Procedure

If critical issues arise:

### 1. Stop New System

```bash
pm2 stop tuhs-abx-v2
```

### 2. Revert Nginx Config

```bash
sudo rm /etc/nginx/sites-enabled/tuhs-abx
sudo ln -s /etc/nginx/sites-available/tuhs-abx-v1 /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Restore Database (if needed)

```bash
gunzip < /backups/tuhs-abx/antibiotic_db_YYYYMMDD.sql.gz | psql antibiotic_db
```

### 4. Notify Stakeholders

Send rollback notification with:
- Issue description
- Rollback time
- Expected resolution time
- Temporary workarounds

---

## Success Criteria

✅ All services running (`pm2 status`, `systemctl status postgresql nginx`)  
✅ Health check returns `{"status":"healthy"}`  
✅ Database has ~180 guideline chunks  
✅ Test recommendations complete in <10s  
✅ SSL certificate valid  
✅ Logs rotating properly  
✅ Backups running daily  
✅ Monitoring alerts configured  
✅ Documentation updated  
✅ Team trained  

---

## Support & Maintenance

### Weekly Tasks
- Review audit logs for anomalies
- Check disk usage (`df -h`)
- Verify backups completed

### Monthly Tasks
- Review performance metrics
- Update dependencies (`npm outdated`)
- Test backup restoration
- Review and archive old logs

### Quarterly Tasks
- Security audit
- Dependency updates
- Model performance review
- User feedback analysis

---

**Deployment Version**: 1.0  
**Last Updated**: October 2025  
**Next Review**: Monthly
