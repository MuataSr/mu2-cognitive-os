# Scripts Directory

This directory contains utility scripts for Mu2 Cognitive OS development and compliance verification.

## Behavioral Tracking Scripts (Phase B)

### useBehavioralTracking
**Frontend Hook** - Tracks user behavioral signals for adaptive UI

**Location**: `apps/web/hooks/use-behavioral-tracking.ts`

**Features**:
- Click/cursor event tracking
- Time-on-task measurement
- Rapid clicking detection
- Batch sending to backend API
- Configurable intervals and batch sizes

**Usage Example**:
```typescript
import { useBehavioralTracking } from '@/hooks/use-behavioral-tracking';

const tracking = useBehavioralTracking({
  userId: 'student-123',
  batchInterval: 5000,  // 5 seconds
  maxBatchSize: 50,
  enabled: true
});

// Record clicks
tracking.recordClick(250, 100, 'submit-button');

// Track task time
tracking.startTaskTimer();
const timeOnTask = tracking.getTimeOnTask();
tracking.stopTaskTimer();

// Get behavioral state
if (tracking.isRapidClicking()) {
  console.log('Rapid clicking detected - user may be frustrated');
}
```

---

## Compliance Scripts

### verify_phase_a_compliance.sh

Quick verification that all Phase A (Compliance & Safety Foundation) requirements are met.

**Usage**:
```bash
./scripts/verify_phase_a_compliance.sh
```

**What it checks**:
- A1: Telemetry kill switch script exists and is executable
- A2: Citation lock files exist and are integrated
- A3: Reduced motion support in CSS and mode provider
- A4: No analytics packages in dependencies
- Additional WCAG 2.1 AA compliance features

**Expected output**:
```
╔══════════════════════════════════════════════════════════════════════╗
║  Phase A Compliance Verification                                    ║
╚════════════════════════════════════════════════════════════════════╝

✓ Phase A Compliance Verified!
All critical FERPA/CIPA/WCAG compliance requirements are met.
```

---

## Phase C: Behavioral Integration (Automatic Mode Switching)

### Mode Provider Behavioral Integration

**File**: `apps/web/components/providers/mode-provider.tsx`

**Features**:
- Polls `/api/v1/behavioral/status/{user_id}` every 10 seconds
- Automatically switches mode when backend suggests different mode
- Enhanced ARIA announcements with urgency context
- Can be toggled on/off via `setAdaptive(false)`

**Usage**:
```typescript
const { mode, isAdaptive, backendSuggestedMode, behavioralUrgency } = useMode();

// Adaptive mode is enabled by default
// Auto-switches to high_contrast_focus when:
// - 3+ consecutive errors detected
// - High urgency frustration signaled
// - Time on task exceeds 2 minutes
```

**Configuration**:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- Polling interval: 10 seconds (adjustable in mode-provider.tsx)
- Adaptive setting persists to localStorage key `mu2-adaptive-enabled`

### Behavioral Status Indicator Component

**File**: `apps/web/components/behavioral-status-indicator.tsx`

**Features**:
- Displays real-time behavioral status from backend
- Shows current/suggested mode badge
- Displays frustration level and urgency
- Shows last update timestamp
- Error handling with ARIA alerts

**Usage**:
```typescript
import { BehavioralStatusIndicator } from '@/components/behavioral-status-indicator';

<BehavioralStatusIndicator
  userId="student-123"
  enabled={true}
  refreshInterval={5000}  // 5 seconds
/>
```

---

## Database Scripts

### migrate-supabase.py

Database migration script for Supabase cloud-hosted database.

---

# Supabase Migration Guide

This guide explains how to connect Mu2 Cognitive OS to a cloud-hosted Supabase database.

## Prerequisites

1. **Supabase Project**: Create a project at [supabase.com](https://supabase.com)
   - Ensure pgvector extension is enabled (should be by default)
   - Note your project region

2. **Database Credentials**: Get from Supabase Dashboard → Settings → Database
   - Connection string (URI format)
   - Database password

3. **API Keys**: Get from Supabase Dashboard → Settings → API
   - Project URL
   - Anon key (public)
   - Service role key (secret - keep safe!)

## Setup Steps

### Step 1: Configure Environment Variables

Copy `.env.example` to `.env` and add your Supabase credentials:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database Connection (from Dashboard → Database → URI)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
```

### Step 2: Install Python Dependencies

```bash
pip install psycopg2-binary python-dotenv
```

### Step 3: Run Migrations

```bash
python scripts/migrate-supabase.py
```

This will apply all migrations in order:
- 001_initial_schema.sql
- 002_knowledge_vault.sql
- 003_mastery_tracking.sql
- 004_add_learning_events_fields.sql

### Step 4: Install Frontend Dependencies

```bash
cd apps/web
npm install
```

### Step 5: Verify Setup

1. **Check Tables**: Go to Supabase Dashboard → Table Editor
   - You should see all cortex.* and vectordb.* tables

2. **Test Backend Connection**:
   ```bash
   cd packages/brain
   uvicorn src.main:app --reload
   curl http://localhost:8000/health
   ```

3. **Test Frontend**:
   ```bash
   cd apps/web
   npm run dev
   ```

## Manual Migration (Alternative)

If the script doesn't work, you can manually run migrations:

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of each migration file (in order)
3. Run each SQL script

## RLS Policies

The migrations include Row Level Security (RLS) policies. To verify they're working:

```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname IN ('cortex', 'vectordb');

-- View policies
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname IN ('cortex', 'vectordb');
```

## Troubleshooting

### Connection Issues

- **Error**: "connection refused"
  - Check DATABASE_URL format
  - Verify password is correct
  - Ensure IP is allowed (Supabase has no IP restrictions by default)

### Extension Not Found

- **Error**: "extension pgvector does not exist"
  - Enable in Supabase Dashboard → Database → Extensions
  - Search for "pgvector" and click Enable

### Migration Fails

- Check error message carefully
- Some errors are expected (e.g., "already exists")
- The script continues on most errors

## Switching Back to Local Docker

To switch back to local development:

```bash
# Stop using Supabase
docker-compose up -d  # Start local Postgres

# Update .env
DATABASE_URL=postgresql://postgres:your-super-secret-and-long-postgres-password@localhost:54322/postgres
```

## Security Notes

1. **Never commit** `.env` file with real credentials
2. **Service Role Key** should only be used server-side
3. **Enable RLS** on all tables with student data
4. **Use Supabase Auth** for user authentication

## FERPA Compliance

When using Supabase cloud:
- Data is encrypted at rest (Supabase default)
- Enable RLS policies
- Use proper authentication
- Consider Supabase Privacy Shield for additional protection

## Next Steps

After migration:
1. Set up Supabase Auth for user authentication
2. Configure storage for file uploads (if needed)
3. Set up real-time subscriptions for live updates
4. Configure backup strategy (Supabase has automatic backups)
