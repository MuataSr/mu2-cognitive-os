#!/bin/bash
################################################################################
# Mu2 Cognitive OS - Update Script
# Safe update mechanism for KDA deployments
#
# Usage: sudo ./update.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/mu2-cognitive-os}"
BACKUP_DIR="/tmp/mu2-backup-$(date +%Y%m%d_%H%M%S)"

print_header() {
    echo -e "${BLUE}"
    echo "================================================================"
    echo "$1"
    echo "================================================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[ ✓ ]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

################################################################################
# Update Process
################################################################################

print_header "Mu2 Cognitive OS - System Update"

check_root

# Check if install directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    print_error "Installation directory not found: $INSTALL_DIR"
    print_info "Run install.sh first"
    exit 1
fi

cd "$INSTALL_DIR"

# Step 1: Run pre-boot compliance check
print_info "Running compliance check before update..."
if [ -f "pre-boot.sh" ]; then
    bash pre-boot.sh
    if [ $? -ne 0 ]; then
        print_error "Compliance check failed - aborting update"
        exit 1
    fi
    print_step "Compliance check passed"
else
    print_warning "pre-boot.sh not found - proceeding without check"
fi

# Step 2: Backup database
print_info "Creating database backup..."
mkdir -p "$BACKUP_DIR"
docker exec mu2-postgres pg_dump -U postgres postgres > "$BACKUP_DIR/database.sql"
print_step "Database backed up to $BACKUP_DIR"

# Step 3: Pull latest code
print_info "Fetching latest code..."
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
print_info "Current commit: $CURRENT_COMMIT"

# Check what would change
git diff HEAD origin/main --stat || git diff HEAD origin/master --stat
print_warning "Review the changes above. Press Ctrl+C to abort, or Enter to continue..."
read

# Pull the changes
git pull origin main || git pull origin master
print_step "Code updated"

# Step 4: Check for new migrations
print_info "Checking for new database migrations..."
NEW_MIGRATIONS=$(git diff HEAD@{1} HEAD --name-only | grep "supabase/migrations/*.sql" || true)

if [ -n "$NEW_MIGRATIONS" ]; then
    print_info "New migrations found:"
    echo "$NEW_MIGRATIONS"
    print_info "Applying new migrations..."

    for migration in $NEW_MIGRATIONS; do
        if [ -f "$migration" ]; then
            migration_name=$(basename "$migration")
            docker exec -i mu2-postgres psql -U postgres -d postgres < "$migration"
            print_step "Applied $migration_name"
        fi
    done
else
    print_info "No new migrations to apply"
fi

# Step 5: Update Python dependencies
print_info "Updating Python dependencies..."
cd "$INSTALL_DIR/packages/brain"
pip3 install -e . --quiet
print_step "Python dependencies updated"

# Step 6: Update Node dependencies
print_info "Updating frontend dependencies..."
cd "$INSTALL_DIR/apps/web"
npm install --silent
print_step "Frontend dependencies updated"

# Step 7: Restart services
print_info "Restarting services..."
cd "$INSTALL_DIR"
docker-compose down
sleep 2
docker-compose up -d
sleep 5

# Verify services are running
if docker-compose ps | grep -q "Up"; then
    print_step "Services restarted successfully"
else
    print_error "Some services failed to start"
    docker-compose ps
    exit 1
fi

# Step 8: Run health checks
print_info "Running health checks..."

# Check database
if docker exec mu2-postgres pg_isready -U postgres &>/dev/null; then
    print_step "Database is healthy"
else
    print_error "Database health check failed"
fi

# Check backend (if health endpoint exists)
if curl -s http://localhost:8000/health &>/dev/null; then
    print_step "Backend API is healthy"
else
    print_warning "Backend health check inconclusive (may still be starting)"
fi

# Check frontend
if curl -s http://localhost:3000 &>/dev/null; then
    print_step "Frontend is healthy"
else
    print_warning "Frontend health check inconclusive (may still be starting)"
fi

# Step 9: Cleanup old backups (keep last 5)
print_info "Cleaning up old backups..."
ls -t /tmp/mu2-backup-* | tail -n +6 | xargs rm -rf 2>/dev/null || true
print_step "Old backups cleaned up"

# Complete
print_header "Update Complete!"

NEW_COMMIT=$(git rev-parse HEAD)
echo ""
echo "Previous commit: $CURRENT_COMMIT"
echo "New commit:      $NEW_COMMIT"
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""
echo "To rollback if needed:"
echo "  1. Stop services: systemctl stop mu2-cognitive-os"
echo "  2. Restore database: docker exec -i mu2-postgres psql -U postgres < $BACKUP_DIR/database.sql"
echo "  3. Revert code: git reset --hard $CURRENT_COMMIT"
echo "  4. Restart services: systemctl start mu2-cognitive-os"
echo ""
print_step "Update completed successfully!"
