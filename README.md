# Mu2 Cognitive OS - Administrator Guide

**Version:** 1.0.0 (Gold Build)
**For:** KDA Administrators and IT Staff
**Deployment:** Local-Only FERPA-Compliant Learning Platform

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [How to Install](#how-to-install)
3. [How to Add Students](#how-to-add-students)
4. [How to Use the Dashboard](#how-to-use-the-dashboard)
5. [Compliance Certifications](#compliance-certifications)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Quick Start

```bash
# One-command installation
sudo ./install.sh

# Access the platform
# Frontend: http://localhost:3000
# Teacher Dashboard: http://localhost:3000/teacher
# API Documentation: http://localhost:8000/docs
```

---

## How to Install

### Prerequisites

- **Operating System:** Linux (Ubuntu 20.04+ recommended)
- **RAM:** 4GB minimum (8GB recommended)
- **Storage:** 20GB free space
- **Required Software:**
  - Docker (auto-installed if missing)
  - Git (auto-installed if missing)

### Installation Steps

#### Option 1: Automated Installation (Recommended)

```bash
# Clone or download the repository
git clone <repository-url>
cd mu2-cognitive-os

# Run the installer
sudo ./install.sh
```

The installer will:
1. Check for prerequisites (Docker, Git, Python3)
2. Clone the repository
3. Start PostgreSQL database
4. Run all database migrations
5. Install Python and Node dependencies
6. Run FERPA compliance check
7. Seed initial content (OpenStax Biology Chapter 5)
8. Create systemd service for auto-startup

#### Option 2: Manual Installation

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install docker.io git python3 python3-pip nodejs npm

# Start database
docker-compose up -d

# Run migrations
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/001_initial_schema.sql
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/002_knowledge_vault.sql
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/003_mastery_tracking.sql

# Install Python backend
cd packages/brain
pip3 install -e .

# Install frontend
cd ../../apps/web
npm install

# Seed content
cd ../packages/brain
python3 scripts/seed_content.py
```

### Verification

After installation, verify the system is running:

```bash
# Check services
docker-compose ps

# Run health check
curl http://localhost:8000/health

# Run compliance check
./pre-boot.sh
```

---

## How to Add Students

### Method 1: Via Teacher Dashboard (Recommended)

1. Navigate to **http://localhost:3000/teacher**
2. Click **"Add Student"** button
3. Enter student information (only UUID is stored - no real names required)
4. Select initial skill level
5. Click **"Create Student"**

### Method 2: Via API

```bash
curl -X POST http://localhost:8000/api/v1/mastery/record \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student-uuid-001",
    "skill_id": "membrane-structure",
    "is_correct": true,
    "attempts": 1
  }'
```

### Method 3: Bulk Import (CSV)

Create a CSV file with student data:

```csv
user_id,initial_skill_level
student-001,9
student-002,8
student-003,9
```

Import via command line:

```bash
python3 scripts/import_students.py students.csv
```

### Assigning Skills to Students

Each student can be assigned specific skills to track:

```sql
-- Insert into skills_registry
INSERT INTO cortex.skills_registry (skill_id, skill_name, subject, grade_level)
VALUES
    ('membrane-structure', 'Plasma Membrane Structure', 'biology', 9),
    ('passive-transport', 'Passive Transport', 'biology', 9),
    ('active-transport', 'Active Transport', 'biology', 9);
```

---

## How to Use the Dashboard

### Teacher Command Center

Navigate to **http://localhost:3000/teacher**

#### Dashboard Features

1. **Student Cards Grid**
   - Red dot = Struggling (needs intervention)
   - Yellow dot = Learning (in progress)
   - Green dot = Mastered (ready for next challenge)

2. **Real-Time Updates**
   - Dashboard refreshes every 5 seconds
   - Changes appear instantly without page reload

3. **Student Detail View**
   - Click any student card to see detailed skill breakdown
   - View mastery probability for each skill
   - See suggested actions for intervention

4. **Filter Options**
   - "All Students" - Shows entire class
   - "Needs Help Only" - Shows only struggling students

### Interpreting the Red Dot

The **Red Dot** appears when:
- A student's mastery probability drops below **60%**
- The student has made **more than 3 attempts**
- The student has **2+ consecutive incorrect answers**

**Suggested Actions:**
- Provide one-on-one remediation
- Offer scaffolded practice problems
- Check for misconceptions
- Consider peer tutoring

### Mastery Probability Explained

| Range | Status | Meaning | Action |
|-------|--------|---------|--------|
| 0-59% | Struggling | Student needs help | Immediate intervention |
| 60-89% | Learning | Making progress | Continue practice |
| 90-100% | Mastered | Ready to advance | Move to next skill |

---

## Compliance Certifications

### FERPA Compliance

✓ **Family Educational Rights and Privacy Act (FERPA) Compliant**

The system meets the following FERPA requirements:

1. **Local-Only Storage**
   - All data stored on localhost (port 54322)
   - No cloud synchronization
   - No external API calls for student data

2. **Data Minimization**
   - Only UUIDs stored (no real names, emails, or PII)
   - Automatic data masking for non-teacher roles
   - No persistent student profiles with identifying information

3. **Access Controls**
   - Row-Level Security (RLS) enabled on all tables
   - Role-based access: Student, Teacher, Admin
   - Audit logging for all data access

4. **No Third-Party Sharing**
   - No analytics or telemetry enabled
   - No data sold or shared with third parties
   - Pre-boot kill script enforces compliance

### WCAG 2.1 AA Compliance

✓ **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA**

Accessibility features:
- **Focus Mode:** High-contrast black/white/yellow theme
- **Keyboard Navigation:** Full keyboard support
- **Screen Reader:** ARIA labels and live regions
- **Reduced Motion:** Respects prefers-reduced-motion
- **Skip Links:** Bypass navigation for screen readers

### COPPA Compliance

✓ **Children's Online Privacy Protection Act (COPPA) Compliant**

- No external tracking or advertising
- No collection of personal information from children
- Parental consent not required (local-only system)

### Security Certifications

✓ **Data Security**

- PostgreSQL database with encryption at rest
- CORS restricted to localhost only
- No open ports to external networks
- SQL injection protection via parameterized queries

✓ **Telemetry-Free**

- Pre-boot script (`pre-boot.sh`) scans for telemetry
- All analytics/analytics packages blocked
- Startup message confirms: "🔒 SECURE MODE ACTIVE: TELEMETRY DISABLED"

---

## Troubleshooting

### Database Won't Start

**Problem:** Docker containers fail to start

**Solution:**
```bash
# Check Docker is running
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Recreate containers
docker-compose down
docker-compose up -d
```

### Dashboard Shows No Students

**Problem:** Teacher dashboard is empty

**Solution:**
```bash
# Check database has data
docker exec -it mu2-postgres psql -U postgres -d postgres
SELECT COUNT(*) FROM cortex.student_skills;

# If empty, seed test data
python3 packages/brain/scripts/seed_content.py
```

### Mastery Not Updating

**Problem:** Student mastery scores not changing after answers

**Solution:**
```bash
# Check trigger is active
docker exec -it mu2-postgres psql -U postgres -d postgres
SELECT tgname FROM pg_trigger WHERE tgname = 'trigger_update_mastery';

# Recreate trigger if missing
\i supabase/migrations/003_mastery_tracking.sql
```

### Compliance Check Fails

**Problem:** Pre-boot script finds telemetry

**Solution:**
```bash
# Run with --force to auto-remove
./pre-boot.sh --force

# Manually check package.json
grep -i "analytics\|telemetry\|posthog\|segment" apps/web/package.json

# Remove offending packages
npm uninstall <package-name>
```

### Frontend Build Errors

**Problem:** npm install fails

**Solution:**
```bash
# Clear cache and reinstall
cd apps/web
rm -rf node_modules package-lock.json
npm install

# If still failing, check Node version
node --version  # Should be >= 18.0.0
```

---

## Maintenance

### Daily Operations

```bash
# Check system health
curl http://localhost:8000/health

# View logs
journalctl -u mu2-cognitive-os -f

# Check disk space
df -h
```

### Weekly Backup

```bash
# Backup database
docker exec mu2-postgres pg_dump -U postgres postgres > backup-$(date +%Y%m%d).sql

# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### System Updates

```bash
# Update to latest version
sudo ./update.sh

# Update includes:
# - Git pull latest code
# - Run new migrations
# - Update dependencies
# - Restart services
# - Create automatic backup
```

### Resetting Student Data (End of Term)

```sql
-- Clear all learning events for a specific student
DELETE FROM cortex.learning_events WHERE user_id = 'student-uuid';

-- Reset mastery to default
UPDATE cortex.student_skills
SET probability_mastery = 0.5,
    total_attempts = 0,
    correct_attempts = 0
WHERE user_id = 'student-uuid';
```

### Viewing Audit Logs

```bash
# View compliance logs
cat logs/compliance.log

# View student access logs
docker exec mu2-postgres psql -U postgres -d postgres
SELECT * FROM audit_log WHERE event_type = 'student_access';
```

---

## Support

### Getting Help

- **Documentation:** See `CLAUDE.md` for developer documentation
- **API Docs:** http://localhost:8000/docs
- **Run Tests:** `pytest packages/brain/tests/`
- **Compliance Check:** `./pre-boot.sh`

### Emergency Shutdown

```bash
# Stop all services immediately
docker-compose down

# Verify stopped
docker-compose ps
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01 | Gold Build - Initial KDA release |

---

## License

Proprietary - For KDA Internal Use Only

---

**© 2025 Mu2 Cognitive OS - FERPA-Compliant Adaptive Learning Platform**
