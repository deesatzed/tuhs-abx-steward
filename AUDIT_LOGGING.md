# Audit Logging

The TUHS Antibiotic Steward includes comprehensive audit logging to track all recommendation requests for compliance, review, and quality improvement.

## Overview

Both the Node.js and Python stacks implement audit logging:
- **Node.js**: `lib/auditLogger.js`
- **Python**: `audit_logger.py`

All logs are stored in the `logs/` directory with date-based filenames.

## Log File Format

### Location
```
logs/audit-YYYY-MM-DD.log
```

Example: `logs/audit-2025-10-04.log`

### Entry Structure

Each log entry is a JSON object on a single line:

```json
{
  "timestamp": "2025-10-04T09:19:50.891717",
  "request_id": "req_1759583990891_a3b2c1d4",
  "status": "success",
  "input": {
    "age": "65",
    "gender": "male",
    "infection_type": "cystitis",
    "gfr": "80",
    "location": "Ward",
    "allergies": "none"
  },
  "category": "cystitis",
  "recommendation_length": 450,
  "tuhs_confidence": 0.85,
  "final_confidence": 0.90,
  "source_count": 4,
  "duration_ms": 1250.5,
  "error": null
}
```

### Fields Logged

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp of request |
| `request_id` | string | Unique request identifier |
| `status` | string | `"success"` or `"error"` |
| `input` | object | Patient data (sanitized, no API keys) |
| `category` | string | Infection category determined |
| `recommendation_length` | number | Length of recommendation text |
| `tuhs_confidence` | float | TUHS guideline confidence (0-1) |
| `final_confidence` | float | Final confidence after evidence search (0-1) |
| `source_count` | number | Number of evidence sources found |
| `duration_ms` | float | Request processing time in milliseconds |
| `error` | string | Error message if status is `"error"` |

## Viewing Audit Logs

### Python Stack

#### View Today's Summary
```bash
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py
```

#### View Specific Date
```bash
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py --date 2025-10-04
```

#### View Past 7 Days
```bash
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py --recent 7
```

#### View Raw Log Entries
```bash
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py --raw
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py --raw --date 2025-10-04
```

### Node.js Stack

#### View Raw Logs
```bash
# Today's log
cat logs/audit-$(date +%Y-%m-%d).log | jq '.'

# Specific date
cat logs/audit-2025-10-04.log | jq '.'

# Tail in real-time
tail -f logs/audit-*.log | jq '.'
```

#### Filter by Status
```bash
# Only successful requests
cat logs/audit-*.log | jq 'select(.status == "success")'

# Only errors
cat logs/audit-*.log | jq 'select(.status == "error")'
```

#### Filter by Category
```bash
# Only cystitis cases
cat logs/audit-*.log | jq 'select(.category == "cystitis")'

# Only pyelonephritis cases
cat logs/audit-*.log | jq 'select(.category == "pyelonephritis")'
```

## API Endpoint (Python Stack)

Get audit summary via API:

```bash
# Today's summary
curl http://localhost:8080/api/audit/summary

# Specific date
curl http://localhost:8080/api/audit/summary?date=2025-10-04
```

Response:
```json
{
  "date": "2025-10-04",
  "total_requests": 15,
  "success_count": 14,
  "error_count": 1,
  "avg_duration_ms": 1350.25,
  "categories": {
    "cystitis": 5,
    "pyelonephritis": 4,
    "pneumonia": 3,
    "skin_soft_tissue": 2
  }
}
```

## Privacy & Security

### Data Sanitization

Sensitive information is automatically redacted from logs:
- API keys
- Authorization tokens
- Any field containing `api_key`, `openrouter_api_key`, `authorization`, `token`

### PHI Considerations

The audit logs contain:
- ✅ De-identified patient demographics (age, gender)
- ✅ Clinical parameters (GFR, weight)
- ✅ Infection types and allergies
- ❌ NO patient names, MRNs, or identifiers

**Note**: Audit logs should still be treated as potentially containing PHI and stored securely with appropriate access controls.

## Log Rotation

### Manual Rotation

Logs are automatically separated by date. To archive old logs:

```bash
# Archive logs older than 30 days
find logs/ -name "audit-*.log" -mtime +30 -exec gzip {} \;

# Move to archive directory
mkdir -p logs/archive
find logs/ -name "audit-*.log.gz" -exec mv {} logs/archive/ \;
```

### Automated Rotation (Production)

For production deployments, configure logrotate:

Create `/etc/logrotate.d/tuhs-abx`:

```
/opt/tuhs-abx-steward/logs/audit-*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    missingok
    create 0640 www-data www-data
}
```

## Programmatic Access

### Python

```python
from audit_logger import get_log_summary
from datetime import datetime

# Get today's summary
summary = get_log_summary()
print(f"Total requests: {summary['total_requests']}")
print(f"Success rate: {summary['success_count'] / summary['total_requests']:.1%}")

# Get specific date
from datetime import datetime
target_date = datetime(2025, 10, 4)
summary = get_log_summary(date=target_date)
```

### Node.js

```javascript
import { readFileSync } from 'node:fs';

const today = new Date().toISOString().split('T')[0];
const logFile = `logs/audit-${today}.log`;

const entries = readFileSync(logFile, 'utf8')
  .split('\n')
  .filter(line => line.trim())
  .map(line => JSON.parse(line));

const totalRequests = entries.length;
const successRate = entries.filter(e => e.status === 'success').length / totalRequests;
console.log(`Success rate: ${(successRate * 100).toFixed(1)}%`);
```

## Compliance & Reporting

### Generate Monthly Report

```bash
/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py --recent 30 > monthly_report.txt
```

### Extract Metrics

```bash
# Average response time per category
cat logs/audit-*.log | jq -s 'group_by(.category) | map({category: .[0].category, avg_duration: (map(.duration_ms) | add / length)})'

# Success rate by category
cat logs/audit-*.log | jq -s 'group_by(.category) | map({category: .[0].category, total: length, success: (map(select(.status == "success")) | length)})'

# Confidence scores distribution
cat logs/audit-*.log | jq -s 'map(.final_confidence) | {min: min, max: max, avg: (add / length)}'
```

## Troubleshooting

### No logs directory

The directory is created automatically on first request. If missing:

```bash
mkdir -p logs
```

### Permission errors

Ensure the application has write permissions:

```bash
chmod 750 logs/
chown -R <app_user>:<app_group> logs/
```

### Large log files

Each day gets a new file, so individual files should remain manageable. If needed, compress old logs:

```bash
gzip logs/audit-2025-*.log
```

## Best Practices

1. **Regular Review**: Review audit logs weekly for errors and anomalies
2. **Archive Old Logs**: Archive logs older than 90 days
3. **Monitor Disk Space**: Set up alerts if `logs/` exceeds expected size
4. **Secure Access**: Restrict log file access to authorized personnel only
5. **Backup**: Include audit logs in regular backup procedures
