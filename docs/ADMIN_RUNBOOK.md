# Mu2 Cognitive OS - Administrator Runbook

**Version:** 1.0.0
**Last Updated:** 2025
**Target Audience:** System Administrators, IT Staff, Technical Support

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Service Management](#service-management)
5. [How to Restart the Server](#how-to-restart-the-server)
6. [How to Update Content via USB](#how-to-update-content-via-usb)
7. [Backup and Recovery](#backup-and-recovery)
8. [Monitoring and Health Checks](#monitoring-and-health-checks)
9. [Troubleshooting Common Issues](#troubleshooting-common-issues)
10. [Security and Compliance](#security-and-compliance)
11. [Fleet Management](#fleet-management)

---

## System Overview

### What is Mu2 Cognitive OS?

Mu2 Cognitive OS is a FERPA-compliant, local-only adaptive learning platform consisting of:

- **Frontend:** Next.js 15 web application (port 3000)
- **Backend:** FastAPI with LangGraph state machine (port 8000)
- **Database:** PostgreSQL 15 with pgvector and Apache AGE (port 54322)
- **LLM:** Ollama (local inference, port 11434)

### Key Constraints

- **No cloud services** - All data stays on the local machine
- **No telemetry** - Pre-boot script blocks all analytics
- **No internet required** after initial setup
- **FERPA-compliant** by design

---

## Architecture

### Service Dependencies

```
┌─────────────┐
│   Browser   │
│  (port 3000)│
└──────┬──────┘
       │
       v
┌─────────────┐
│  Frontend   │
│   (Next.js) │
└──────┬──────┘
       │
       v
┌─────────────┐
│   Backend   │
│  (FastAPI)  │
│  (port 8000)│
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       v              v              v
┌──────────┐  ┌──────────┐  ┌──────────┐
│Postgres  │  │ Ollama   │  │ SQLite   │
│(54322)   │  │ (11434)  │  │(vector)  │
└──────────┘  └──────────┘  └──────────┘
```

### Directory Structure

```
/opt/mu2-cognitive-os/
├── apps/
│   └── web/                 # Next.js frontend
│       ├── .next/           # Build output
│       ├── node_modules/    # Dependencies
│       └── package.json
├── packages/
│   └── brain/               # FastAPI backend
│       ├── src/
│       │   ├── core/        # Config, state management
│       │   ├── graph/       # LangGraph state machine
│       │   └── services/    # Business logic
│       ├── tests/           # Test suite
│       └── pyproject.toml
├── supabase/migrations/     # Database schema files
├── docker-compose.yml       # Container orchestration
├── install.sh               # Installation script
├── pre-boot.sh              # FERPA compliance check
└── scripts/
    ├── health-check-fleet.sh
    ├── make-usb-installer.sh
    └── generate-audit-report.sh
```

---

## Installation

### Prerequisites

- **OS:** Ubuntu 20.04+ or similar Linux distribution
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 20GB minimum
- **Software:**
  - Docker 20.10+
  - Docker Compose 2.0+
  - Git
  - Python 3.11+
  - Node.js 18+

### Quick Install

```bash
# Clone or copy the repository
cd /opt/mu2-cognitive-os

# Run the installation script
sudo ./install.sh
```

### Manual Install

```bash
# 1. Start Docker services
docker-compose up -d

# 2. Wait for database to initialize
sleep 10

# 3. Run database migrations
for migration in supabase/migrations/*.sql; do
    docker exec -i mu2-postgres psql -U postgres -d postgres < "$migration"
done

# 4. Install Python dependencies
cd packages/brain
pip install -e .

# 5. Install Node dependencies
cd ../../apps/web
npm install

# 6. Run pre-boot compliance check
cd ../..
./pre-boot.sh
```

---

## Service Management

### Starting All Services

```bash
cd /opt/mu2-cognitive-os
docker-compose up -d
```

### Stopping All Services

```bash
docker-compose down
```

### Checking Service Status

```bash
docker-compose ps
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mu2-postgres
```

---

## How to Restart the Server

### Scenario 1: Quick Restart (All Services)

```bash
cd /opt/mu2-cognitive-os
docker-compose restart
```

**Expected downtime:** ~30 seconds

### Scenario 2: Graceful Restart (Production)

```bash
cd /opt/mu2-cognitive-os

# 1. Stop services gracefully
docker-compose down

# 2. Wait for cleanup
sleep 5

# 3. Start services
docker-compose up -d

# 4. Verify health
./scripts/health-check-fleet.sh
```

**Expected downtime:** ~1-2 minutes

### Scenario 3: Restart Specific Service

```bash
# Restart only the database
docker-compose restart mu2-postgres

# Restart only the backend
# (If running as a service)
systemctl restart mu2-backend
```

### Scenario 4: Crash Recovery

If the system crashes or becomes unresponsive:

```bash
# 1. Force stop all containers
docker-compose down -v

# 2. Remove orphaned containers
docker container prune -f

# 3. Restart
docker-compose up -d

# 4. Run health check
./scripts/health-check-fleet.sh
```

### Systemd Service (Auto-start)

Mu2 installs a systemd service for automatic startup:

```bash
# Check service status
systemctl status mu2-cognitive-os

# Start service
systemctl start mu2-cognitive-os

# Stop service
systemctl stop mu2-cognitive-os

# Enable at boot
systemctl enable mu2-cognitive-os

# View logs
journalctl -u mu2-cognitive-os -f
```

---

## How to Update Content via USB

### Preparing the USB Update

1. **Create the USB installer on an internet-connected machine:**

```bash
./scripts/make-usb-installer.sh
```

This creates a `mu2-usb` folder with:
- Updated code
- Docker images
- Installation scripts

2. **Copy to USB drive:**
```bash
cp -r mu2-usb /media/USB_DRIVE/
```

### Applying the Update (Air-gapped Machine)

1. **Copy from USB to the target machine:**
```bash
cp -r /media/USB_DRIVE/mu2-usb /tmp/
```

2. **Stop running services:**
```bash
cd /opt/mu2-cognitive-os
docker-compose down
```

3. **Backup current installation (optional but recommended):**
```bash
cp -r /opt/mu2-cognitive-os /opt/mu2-cognitive-os.backup.$(date +%Y%m%d)
```

4. **Replace the installation:**
```bash
rm -rf /opt/mu2-cognitive-os/*
cp -r /tmp/mu2-usb/* /opt/mu2-cognitive-os/
```

5. **Load Docker images:**
```bash
cd /opt/mu2-cognitive-os
./load-docker-images.sh
```

6. **Restart services:**
```bash
docker-compose up -d
```

7. **Verify update:**
```bash
./scripts/health-check-fleet.sh
```

### Content-Only Updates (No Code Changes)

If you only need to update textbook content:

```bash
# 1. Connect to the database
docker exec -it mu2-postgres psql -U postgres -d postgres

# 2. Clear existing content
DELETE FROM cortex.textbook_chunks;

# 3. Load new content
\i /path/to/new/content.sql

# 4. Exit
\q
```

---

## Backup and Recovery

### Database Backup

```bash
# Automatic backup with timestamp
docker exec mu2-postgres pg_dump -U postgres postgres > \
    backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker exec mu2-postgres pg_dump -U postgres postgres | \
    gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database Restore

```bash
# From SQL file
docker exec -i mu2-postgres psql -U postgres postgres < backup_file.sql

# From compressed file
gunzip -c backup_file.sql.gz | \
    docker exec -i mu2-postgres psql -U postgres postgres
```

### Full System Backup

```bash
# Backup entire installation
tar -czf mu2_backup_$(date +%Y%m%d).tar.gz /opt/mu2-cognitive-os

# Include Docker volumes
docker run --rm -v mu2_postgres_data:/data -v \
    $(pwd):/backup alpine tar -czf /backup/postgres_data_$(date +%Y%m%d).tar.gz /data
```

---

## Monitoring and Health Checks

### Quick Health Check

```bash
./scripts/health-check-fleet.sh
```

**Exit codes:**
- `0` = GREEN (all systems operational)
- `1` = YELLOW (degraded performance)
- `2` = RED (critical failures)

### Detailed Health Check

```bash
# Check all Docker containers
docker ps

# Check database connectivity
docker exec mu2-postgres pg_isready -U postgres

# Check frontend
curl -I http://localhost:3000

# Check backend
curl http://localhost:8000/health

# Check database port
nc -z localhost 54322 && echo "DB port open" || echo "DB port closed"
```

### Monitoring Commands

```bash
# Resource usage
docker stats

# Disk usage
df -h

# Memory usage
free -h

# Process status
ps aux | grep -E "docker|uvicorn|node"
```

---

## Troubleshooting Common Issues

### Issue: Frontend Won't Load (Port 3000)

**Symptoms:** Browser shows "Connection refused" or "ERR_CONNECTION_REFUSED"

**Diagnosis:**
```bash
# Check if frontend is running
curl http://localhost:3000

# Check Next.js process
ps aux | grep next
```

**Solutions:**
1. **Restart frontend:**
   ```bash
   cd /opt/mu2-cognitive-os/apps/web
   npm run dev
   ```

2. **Check port conflicts:**
   ```bash
   lsof -i :3000
   # Kill conflicting process if needed
   ```

3. **Clear Next.js cache:**
   ```bash
   cd /opt/mu2-cognitive-os/apps/web
   rm -rf .next
   npm run dev
   ```

### Issue: Backend Returns 500 Errors

**Symptoms:** API calls fail with status 500

**Diagnosis:**
```bash
# Check backend logs
docker-compose logs mu2-postgres
# Or if running standalone:
journalctl -u mu2-backend -n 50
```

**Solutions:**
1. **Restart backend:**
   ```bash
   cd /opt/mu2-cognitive-os/packages/brain
   uvicorn src.main:app --reload
   ```

2. **Check database connection:**
   ```bash
   docker exec mu2-postgres pg_isready -U postgres
   ```

3. **Verify migrations:**
   ```bash
   docker exec -i mu2-postgres psql -U postgres -d postgres \
       -c "SELECT tablename FROM pg_tables WHERE schemaname = 'cortex';"
   ```

### Issue: Database Won't Start

**Symptoms:** `docker-compose up` fails, database container exits immediately

**Diagnosis:**
```bash
# Check database logs
docker-compose logs mu2-postgres

# Check disk space
df -h
```

**Solutions:**
1. **Check disk space** (must have at least 5GB free)
2. **Remove corrupted volume** (WARNING: deletes data):
   ```bash
   docker-compose down -v
   docker volume rm mu2_postgres_data
   docker-compose up -d
   ```
3. **Restore from backup** (if available)

### Issue: High Memory Usage

**Symptoms:** System becomes slow, high RAM usage

**Diagnosis:**
```bash
free -h
docker stats
```

**Solutions:**
1. **Restart services:**
   ```bash
   docker-compose restart
   ```

2. **Limit Docker memory:**
   Edit `/etc/docker/daemon.json`:
   ```json
   {
     "default-runtime": "runc",
     "default-ulimits": {
       "mem": {
         "Name": "mem",
         "Hard": 2147483648,
         "Soft": 2147483648
       }
     }
   }
   ```

3. **Restart Docker:**
   ```bash
   systemctl restart docker
   ```

### Issue: Pre-boot Check Fails

**Symptoms:** `./pre-boot.sh` exits with error

**Diagnosis:** Check the output for specific violations

**Solutions:**
1. **Remove telemetry dependencies:**
   ```bash
   ./pre-boot.sh --force
   ```

2. **Manually review package.json:**
   ```bash
   grep -E "analytics|telemetry|posthog|plausible" apps/web/package.json
   ```

---

## Security and Compliance

### FERPA Compliance Checklist

- [ ] All data stored on localhost only
- [ ] No cloud services configured
- [ ] No telemetry or analytics enabled
- [ ] Pre-boot check passes (`./pre-boot.sh`)
- [ ] Database encrypted at rest
- [ ] Teacher accounts secured with strong passwords
- [ ] Student IDs masked for privacy

### Running the Audit Report

```bash
./scripts/generate-audit-report.sh
```

This generates `CERTIFICATE_OF_COMPLIANCE_[DATE].txt` with:
- FERPA status
- Telemetry check
- Encryption status
- Test suite results

### Firewall Configuration

Allow only local access:

```bash
# Allow localhost only
ufw allow from 127.0.0.1 to any port 3000
ufw allow from 127.0.0.1 to any port 8000
ufw allow from 127.0.0.1 to any port 54322

# Deny external access
ufw deny 3000
ufw deny 8000
ufw deny 54322
```

---

## Fleet Management

### Deploying to 50+ Machines

1. **Create USB installer:**
   ```bash
   ./scripts/make-usb-installer.sh
   ```

2. **Duplicate USB drives** (one per machine)

3. **On each machine:**
   ```bash
   sudo ./mu2-usb/load-docker-images.sh
   sudo ./mu2-usb/install.sh
   ./mu2-usb/verify-installation.sh
   ```

4. **Verify all machines:**
   ```bash
   # Run via SSH across fleet
   for host in host1 host2 host3 ...; do
       ssh $host "cd /opt/mu2-cognitive-os && ./scripts/health-check-fleet.sh --quiet"
   done
   ```

### Bulk Health Check Script

```bash
#!/bin/bash
# check_fleet.sh - Check all machines in fleet

HOSTS=(
    "classroom-pc-01"
    "classroom-pc-02"
    "classroom-pc-03"
    # ... add all hosts
)

GREEN=0
YELLOW=0
RED=0

for host in "${HOSTS[@]}"; do
    status=$(ssh $host "cd /opt/mu2-cognitive-os && ./scripts/health-check-fleet.sh --quiet" 2>/dev/null || echo "2")

    case $status in
        0) echo "✓ $host: GREEN"; GREEN=$((GREEN + 1));;
        1) echo "! $host: YELLOW"; YELLOW=$((YELLOW + 1));;
        2) echo "✗ $host: RED"; RED=$((RED + 1));;
    esac
done

echo ""
echo "Fleet Summary:"
echo "  GREEN:  $GREEN"
echo "  YELLOW: $YELLOW"
echo "  RED:    $RED"
```

---

## Emergency Procedures

### Emergency Shutdown

```bash
# Immediate stop
docker-compose down

# Force stop if needed
docker-compose down -f

# Kill all Mu2 processes
pkill -f "uvicorn|next|node"
docker kill $(docker ps -q)
```

### Data Recovery Procedure

1. **Stop all services**
2. **Restore database from backup**
3. **Restart services**
4. **Verify with health check**

### Disaster Recovery

If the entire machine fails:

1. **Procure replacement hardware**
2. **Install Docker and dependencies**
3. **Run install.sh from USB**
4. **Restore database from backup**
5. **Verify all services**

---

## Contact and Support

### Getting Help

- **Documentation:** `docs/` folder
- **Issues:** Check logs first, then contact support
- **Updates:** Use USB installer method

### Useful Commands Summary

```bash
# Health check
./scripts/health-check-fleet.sh

# Restart everything
docker-compose restart

# View logs
docker-compose logs -f

# Database access
docker exec -it mu2-postgres psql -U postgres -d postgres

# Backup
docker exec mu2-postgres pg_dump -U postgres postgres > backup.sql

# Compliance check
./pre-boot.sh

# Generate audit report
./scripts/generate-audit-report.sh
```

---

**End of Administrator Runbook**

For questions or issues, please refer to the project documentation or contact the system administrator.
