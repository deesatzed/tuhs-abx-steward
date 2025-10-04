# Fly.io CLI Commands Reference

## Essential Commands for This Project

### Deployment Commands

```bash
# Standard deployment (uses cache)
flyctl deploy

# Force rebuild without cache (use when files aren't updating)
flyctl deploy --no-cache

# Force rebuild and restart all machines
flyctl deploy --no-cache --force-machines

# Deploy with specific Dockerfile
flyctl deploy --dockerfile Dockerfile

# Deploy and watch logs in real-time
flyctl deploy && flyctl logs
```

### App Management

```bash
# Show app status
flyctl status

# List all your apps
flyctl apps list

# Show app details
flyctl info

# Restart the app (faster than redeploying)
flyctl apps restart

# Scale app (useful for forcing refresh)
flyctl scale count 1

# Stop all machines
flyctl scale count 0

# Start machines again
flyctl scale count 2
```

### Machine Management

```bash
# List all machines
flyctl machines list

# Restart a specific machine
flyctl machines restart <machine-id>

# Restart all machines (forces code reload)
flyctl machines restart --all

# Stop all machines
flyctl machines stop --all

# Start all machines
flyctl machines start --all

# Destroy and recreate machines (nuclear option)
flyctl machines destroy <machine-id> --force
```

### SSH & Console Access

```bash
# SSH into running machine
flyctl ssh console

# SSH and run a command
flyctl ssh console -C "cat /app/agno_bridge_v2.py | head -100"

# Check if specific code is deployed
flyctl ssh console -C "grep 'PYELONEPHRITIS-SPECIFIC WARNINGS' /app/agno_bridge_v2.py"

# Verify Python packages
flyctl ssh console -C "pip list | grep agno"

# Check file timestamps (to verify fresh deploy)
flyctl ssh console -C "ls -la /app/agno_bridge_v2.py"

# View environment variables
flyctl ssh console -C "env | grep OPENROUTER"

# Test API endpoint from inside container
flyctl ssh console -C "curl -s http://localhost:8080/api/health"
```

### Logs & Debugging

```bash
# Stream live logs
flyctl logs

# Show recent logs
flyctl logs --recent

# Show logs from specific machine
flyctl logs -i <machine-id>

# Filter logs by text
flyctl logs | grep "pyelonephritis"

# Save logs to file
flyctl logs > deployment_logs.txt
```

### Secrets Management

```bash
# List secrets
flyctl secrets list

# Set a secret (forces app restart)
flyctl secrets set OPENROUTER_API_KEY=your-key-here

# Set multiple secrets
flyctl secrets set KEY1=value1 KEY2=value2

# Remove a secret
flyctl secrets unset SECRET_NAME

# Import secrets from .env file
flyctl secrets import < .env
```

### File & Config Verification

```bash
# Check deployed file content
flyctl ssh console -C "head -200 /app/agno_bridge_v2.py"

# Count specific lines in deployed file
flyctl ssh console -C "grep -c 'PYELONEPHRITIS-SPECIFIC WARNINGS' /app/agno_bridge_v2.py"

# Check if temperature setting is present
flyctl ssh console -C "grep 'temperature=0.1' /app/agno_bridge_v2.py"

# Verify ABXguideInp.json is present
flyctl ssh console -C "ls -lh /app/ABXguideInp.json"

# Check running Python process
flyctl ssh console -C "ps aux | grep python"

# Test instruction generation on server
flyctl ssh console -C "python3 -c 'from agno_bridge_v2 import TUHSGuidelineLoader; loader = TUHSGuidelineLoader(); instructions = loader.build_agent_instructions(\"Urinary Tract\", subsection_filter=\"Pyelonephritis\"); print(len(instructions))'"
```

### Testing Deployed API

```bash
# Test health endpoint
curl https://tuhs-abx-steward.fly.dev/api/health

# Test with simple request
curl -X POST https://tuhs-abx-steward.fly.dev/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age":"33","gender":"female","infection_type":"pyelonephritis","allergies":"None"}'

# Test and save response
curl -X POST https://tuhs-abx-steward.fly.dev/api/recommendation \
  -H "Content-Type: application/json" \
  -d @test_case.json > response.json
```

### Docker Image Management

```bash
# List Docker images
flyctl image show

# Force a complete rebuild (deletes cached layers)
flyctl deploy --build-only --no-cache

# Check build logs
flyctl builds list
```

### Volume & Data Management

```bash
# List volumes (if using persistent storage)
flyctl volumes list

# Create a volume
flyctl volumes create data --size 1

# Delete a volume
flyctl volumes delete <volume-id>
```

### App Destruction & Recreation

```bash
# Destroy app completely
flyctl apps destroy tuhs-abx-steward

# Create new app
flyctl apps create tuhs-abx-steward

# Launch new app (interactive)
flyctl launch

# Deploy after recreation
flyctl deploy
```

### Configuration

```bash
# View current fly.toml
cat fly.toml

# Validate fly.toml
flyctl config validate

# Show app configuration
flyctl config show

# Update app configuration
flyctl config save
```

### Monitoring & Performance

```bash
# View metrics
flyctl metrics

# Check resource usage
flyctl status --all

# View release history
flyctl releases

# Rollback to previous release
flyctl releases rollback <version>
```

## Troubleshooting Workflow for Code Not Updating

If deployed code doesn't match GitHub:

```bash
# 1. Verify local file is correct
grep "PYELONEPHRITIS-SPECIFIC WARNINGS" agno_bridge_v2.py

# 2. Verify GitHub has correct file
curl -s "https://raw.githubusercontent.com/deesatzed/tuhs-abx-steward/main/agno_bridge_v2.py" | grep "PYELONEPHRITIS-SPECIFIC WARNINGS"

# 3. Check what's deployed
flyctl ssh console -C "grep 'PYELONEPHRITIS-SPECIFIC WARNINGS' /app/agno_bridge_v2.py"

# 4. If different, force rebuild without cache
flyctl deploy --no-cache --force-machines

# 5. Wait for deployment
sleep 30

# 6. Verify again
flyctl ssh console -C "grep 'PYELONEPHRITIS-SPECIFIC WARNINGS' /app/agno_bridge_v2.py"

# 7. Test the API
curl -X POST https://tuhs-abx-steward.fly.dev/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age":"33","gender":"female","infection_type":"pyelonephritis","allergies":"Penicillin (rash)"}'
```

## Quick Reference: Force Complete Refresh

```bash
# Nuclear option - completely destroy and rebuild
flyctl apps destroy tuhs-abx-steward --yes && \
flyctl apps create tuhs-abx-steward && \
flyctl secrets set OPENROUTER_API_KEY=your-key-here -a tuhs-abx-steward && \
flyctl deploy --no-cache -a tuhs-abx-steward
```

## Common Issues & Fixes

### Issue: Changes not appearing after deploy
```bash
# Solution 1: Force no-cache rebuild
flyctl deploy --no-cache

# Solution 2: Restart machines
flyctl machines restart --all

# Solution 3: Destroy and recreate
flyctl apps destroy tuhs-abx-steward --yes
flyctl launch
```

### Issue: API returning old responses
```bash
# Check if code is updated
flyctl ssh console -C "cat /app/agno_bridge_v2.py | grep -A 5 'PYELONEPHRITIS-SPECIFIC'"

# Restart Python process
flyctl machines restart --all
```

### Issue: Can't SSH into machine
```bash
# Check if machines are running
flyctl status

# Start machines if stopped
flyctl machines start --all

# Scale up if count is 0
flyctl scale count 1
```

### Issue: Deployment hangs
```bash
# Cancel deployment
Ctrl+C

# Check status
flyctl status

# Try again with verbose logging
flyctl deploy --no-cache --verbose
```

## Auto-restart on File Change

```bash
# Watch for changes and auto-deploy
while true; do
  git pull
  flyctl deploy --no-cache
  sleep 60
done
```

## Useful Aliases (add to ~/.bashrc or ~/.zshrc)

```bash
alias fly-deploy='flyctl deploy --no-cache --force-machines'
alias fly-logs='flyctl logs'
alias fly-status='flyctl status'
alias fly-ssh='flyctl ssh console'
alias fly-restart='flyctl machines restart --all'
alias fly-test='curl -X POST https://tuhs-abx-steward.fly.dev/api/recommendation -H "Content-Type: application/json" -d @test_case.json'
```

## Documentation

- Fly.io Docs: https://fly.io/docs/
- Fly.io CLI Reference: https://fly.io/docs/flyctl/
- Troubleshooting: https://fly.io/docs/getting-started/troubleshooting/
