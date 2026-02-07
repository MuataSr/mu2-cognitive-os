#!/bin/bash
################################################################################
# Mu2 Cognitive OS - One-Click Installer
# For KDA deployment on 50 Mini-PCs
#
# Usage: sudo ./install.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="${REPO_URL:-https://github.com/your-org/mu2-cognitive-os.git}"
INSTALL_DIR="${INSTALL_DIR:-/opt/mu2-cognitive-os}"
DB_PORT="${DB_PORT:-54322}"
DOCKER_COMPOSE_VERSION="2.20.0"

################################################################################
# Helper Functions
################################################################################

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

check_command() {
    if command -v "$1" &> /dev/null; then
        print_step "$1 is installed"
        return 0
    else
        print_warning "$1 is NOT installed"
        return 1
    fi
}

################################################################################
# Installation Steps
################################################################################

print_header "Mu2 Cognitive OS - One-Click Installer"

# Check root privileges
check_root

# Step 1: Check prerequisites
print_info "Checking prerequisites..."

MISSING_DEPS=0

if ! check_command "docker"; then
    MISSING_DEPS=1
fi

if ! check_command "git"; then
    MISSING_DEPS=1
fi

if ! check_command "python3"; then
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing required dependencies. Please install:"
    echo "  - Docker: curl -fsSL https://get.docker.com | sh"
    echo "  - Git: apt-get install git"
    echo "  - Python3: apt-get install python3 python3-pip"
    exit 1
fi

# Step 2: Clone or update repository
print_info "Setting up installation directory..."

if [ -d "$INSTALL_DIR" ]; then
    print_info "Directory exists, updating..."
    cd "$INSTALL_DIR"
    git pull origin main || git pull origin master
else
    print_info "Cloning repository..."
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Step 3: Stop existing containers if running
print_info "Stopping any existing containers..."
cd "$INSTALL_DIR"
docker-compose down 2>/dev/null || true

# Step 4: Start Docker services
print_info "Starting Docker services..."
docker-compose up -d

# Wait for database to be ready
print_info "Waiting for database to initialize..."
sleep 10

MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker exec mu2-postgres pg_isready -U postgres 2>/dev/null; then
        print_step "Database is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
    echo -n "."
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    print_error "Database failed to start"
    exit 1
fi

# Step 5: Run database migrations
print_info "Running database migrations..."

# Run migrations in order
for migration in supabase/migrations/*.sql; do
    if [ -f "$migration" ]; then
        migration_name=$(basename "$migration")
        print_info "Applying migration: $migration_name"
        docker exec -i mu2-postgres psql -U postgres -d postgres < "$migration"
        print_step "Applied $migration_name"
    fi
done

# Step 6: Install Python dependencies
print_info "Installing Python dependencies..."
cd "$INSTALL_DIR/packages/brain"
pip3 install -e . --quiet

# Step 7: Install Node dependencies
print_info "Installing frontend dependencies..."
cd "$INSTALL_DIR/apps/web"
npm install --silent

# Step 8: Run pre-boot compliance check
print_info "Running FERPA compliance check..."
if [ -f "$INSTALL_DIR/pre-boot.sh" ]; then
    bash "$INSTALL_DIR/pre-boot.sh"
    if [ $? -eq 0 ]; then
        print_step "Compliance check passed"
    else
        print_error "Compliance check failed - aborting installation"
        exit 1
    fi
else
    print_warning "pre-boot.sh not found - skipping compliance check"
fi

# Step 9: Seed initial content
print_info "Seeding initial content..."
if [ -f "$INSTALL_DIR/packages/brain/scripts/seed_content.py" ]; then
    cd "$INSTALL_DIR/packages/brain"
    python3 scripts/seed_content.py
    print_step "Content seeded successfully"
else
    print_warning "seed_content.py not found - skipping content seeding"
fi

# Step 10: Create systemd service (optional)
print_info "Creating systemd service..."

cat > /etc/systemd/system/mu2-cognitive-os.service << EOF
[Unit]
Description=Mu2 Cognitive OS
After=docker.service
Requires=docker.service

[Service]
Type=forking
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
Restart=on-failure
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mu2-cognitive-os.service
print_step "Systemd service created and enabled"

# Step 11: Create admin user script
print_info "Creating admin helper script..."

cat > "$INSTALL_DIR/add_admin.sh" << 'EOFSCRIPT'
#!/bin/bash
# Add an admin user to Mu2 Cognitive OS

if [ -z "$1" ]; then
    echo "Usage: ./add_admin.sh <email>"
    exit 1
fi

EMAIL="$1"
docker exec -it mu2-postgres psql -U postgres -d postgres << EOSQL
INSERT INTO cortex.admin_users (email, role, created_at)
VALUES ('$EMAIL', 'admin', NOW())
ON CONFLICT (email) DO UPDATE SET role = 'admin';
EOSQL

echo "Admin user $EMAIL added successfully"
EOFSCRIPT

chmod +x "$INSTALL_DIR/add_admin.sh"
print_step "Admin helper script created"

# Step 12: Display completion message
print_header "Installation Complete!"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Mu2 Cognitive OS is now installed and running!         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Service URLs:"
echo "  • Frontend:      http://localhost:3000"
echo "  • Backend API:   http://localhost:8000"
echo "  • API Docs:      http://localhost:8000/docs"
echo "  • Database:      localhost:$DB_PORT"
echo ""
echo "Management Commands:"
echo "  • Start service:     systemctl start mu2-cognitive-os"
echo "  • Stop service:      systemctl stop mu2-cognitive-os"
echo "  • View logs:         journalctl -u mu2-cognitive-os -f"
echo "  • Update system:     cd $INSTALL_DIR && ./update.sh"
echo "  • Add admin user:    cd $INSTALL_DIR && ./add_admin.sh <email>"
echo ""
echo "Compliance:"
echo "  • All data is stored locally (localhost only)"
echo "  • No telemetry or analytics enabled"
echo "  • FERPA-compliant data handling"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Run 'pre-boot.sh' before any development to verify compliance."
echo ""
print_step "Installation completed successfully!"

# Optional: Open browser (commented out for headless installs)
# if command -v xdg-open &> /dev/null; then
#     xdg-open "http://localhost:3000" 2>/dev/null &
# fi
