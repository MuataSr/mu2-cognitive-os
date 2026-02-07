#!/bin/bash
################################################################################
# Mu2 Cognitive OS - USB Installer Creator
# For fleet deployment across 50+ air-gapped Mini-PCs
#
# Usage: ./scripts/make-usb-installer.sh
#
# This script:
# 1. Creates a mu2-usb folder with all installation files
# 2. Exports Docker images as .tar files for air-gapped installation
# 3. Packages everything for easy USB stick deployment
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
USB_DIR="${USB_DIR:-./mu2-usb}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_IMAGES=(
    "postgres:15-alpine"
    "ghcr.io/chroma-core/chroma:latest"
)

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

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    print_step "Docker is available"
}

check_docker_running() {
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_step "Docker daemon is running"
}

################################################################################
# Main Installation Steps
################################################################################

main() {
    print_header "Mu2 Cognitive OS - USB Installer Creator"

    # Check prerequisites
    print_info "Checking prerequisites..."
    check_docker
    check_docker_running

    # Create USB directory
    print_info "Creating USB installer directory..."
    if [ -d "$USB_DIR" ]; then
        print_warning "Removing existing mu2-usb directory..."
        rm -rf "$USB_DIR"
    fi
    mkdir -p "$USB_DIR"
    print_step "Created directory: $USB_DIR"

    # Copy repository files
    print_info "Copying repository files..."
    rsync -av \
        --exclude='node_modules' \
        --exclude='.next' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.git' \
        --exclude='dist' \
        --exclude='build' \
        --exclude='mu2-usb' \
        --exclude='.env.local' \
        --exclude='*.log' \
        "$REPO_DIR/" "$USB_DIR/"
    print_step "Copied repository files"

    # Export Docker images
    print_info "Exporting Docker images for air-gapped installation..."
    mkdir -p "$USB_DIR/docker-images"

    # Pull and export PostgreSQL image
    print_info "Pulling postgres:15-alpine..."
    docker pull postgres:15-alpine
    print_info "Exporting postgres:15-alpine..."
    docker save postgres:15-alpine -o "$USB_DIR/docker-images/postgres-15-alpine.tar"
    print_step "Exported postgres:15-alpine"

    # Pull and export Chroma image (if used)
    if docker images | grep -q "chroma"; then
        print_info "Exporting chroma image..."
        docker save ghcr.io/chroma-core/chroma:latest -o "$USB_DIR/docker-images/chroma-latest.tar" 2>/dev/null || true
        print_step "Exported chroma image"
    fi

    # Create image loading script
    print_info "Creating Docker image loading script..."
    cat > "$USB_DIR/load-docker-images.sh" << 'EOFSCRIPT'
#!/bin/bash
# Load Docker images from tar files
# Usage: ./load-docker-images.sh

set -e

echo "Loading Docker images for Mu2 Cognitive OS..."

for image_file in docker-images/*.tar; do
    if [ -f "$image_file" ]; then
        echo "Loading: $image_file"
        docker load -i "$image_file"
    fi
done

echo "Docker images loaded successfully!"
EOFSCRIPT
    chmod +x "$USB_DIR/load-docker-images.sh"
    print_step "Created load-docker-images.sh"

    # Create README on the USB stick
    print_info "Creating USB README..."
    cat > "$USB_DIR/README_USB.txt" << 'EOFREADME'
Mu2 Cognitive OS - USB Installer Kit
=====================================

This USB contains everything needed to install Mu2 Cognitive OS on an
air-gapped Mini-PC without internet access.

QUICK START:
------------

1. Copy the entire mu2-usb folder to the target machine
2. On the target machine, run:
   cd mu2-usb
   sudo ./load-docker-images.sh
   sudo ./install.sh

3. After installation, access:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

CONTENTS:
---------

Repository Files:
  - apps/web/          Next.js frontend application
  - packages/brain/    FastAPI backend with LangGraph
  - supabase/migrations/  Database schema files
  - install.sh         Main installation script

Docker Images:
  - docker-images/postgres-15-alpine.tar
  - docker-images/chroma-latest.tar (optional)

Scripts:
  - load-docker-images.sh  Load Docker images from tar files
  - install.sh              Main installation script
  - pre-boot.sh             FERPA compliance check

Documentation:
  - docs/TEACHER_GUIDE.md    Guide for teachers
  - docs/ADMIN_RUNBOOK.md    System administration guide

COMPLIANCE:
-----------

✓ FERPA-compliant - all data stays local
✓ No telemetry or analytics
✓ No internet connection required after installation

TROUBLESHOOTING:
---------------

1. If Docker fails to load images:
   - Verify Docker is installed: docker --version
   - Verify Docker is running: docker info

2. If installation fails:
   - Check pre-boot.sh compliance check output
   - Verify ports 3000, 8000, 54322 are available

3. After installation:
   - Run: ./scripts/health-check-fleet.sh
   - Expected output: GREEN status

SUPPORT:
--------

For issues or questions, contact the Mu2 Cognitive OS team.

Version: 1.0.0
Date: $(date)
EOFREADME
    print_step "Created README_USB.txt"

    # Create installation verification script
    print_info "Creating installation verification script..."
    cat > "$USB_DIR/verify-installation.sh" << 'EOFVERIFY'
#!/bin/bash
# Verify Mu2 Cognitive OS installation
# Usage: ./verify-installation.sh

echo "Verifying Mu2 Cognitive OS installation..."

errors=0

# Check Docker
if command -v docker &> /dev/null; then
    echo "✓ Docker is installed"
else
    echo "✗ Docker is NOT installed"
    errors=$((errors + 1))
fi

# Check Docker is running
if docker info &> /dev/null; then
    echo "✓ Docker daemon is running"
else
    echo "✗ Docker daemon is NOT running"
    errors=$((errors + 1))
fi

# Check if Mu2 containers are running
if docker ps | grep -q "mu2-postgres"; then
    echo "✓ Database container is running"
else
    echo "✗ Database container is NOT running"
    errors=$((errors + 1))
fi

# Check frontend port
if curl -s http://localhost:3000 > /dev/null; then
    echo "✓ Frontend is accessible on port 3000"
else
    echo "✗ Frontend is NOT accessible on port 3000"
    errors=$((errors + 1))
fi

# Check backend port
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Backend API is accessible on port 8000"
else
    echo "✗ Backend API is NOT accessible on port 8000"
    errors=$((errors + 1))
fi

# Check database port
if nc -z localhost 54322 2>/dev/null; then
    echo "✓ Database is accessible on port 54322"
else
    echo "✗ Database is NOT accessible on port 54322"
    errors=$((errors + 1))
fi

echo ""
if [ $errors -eq 0 ]; then
    echo "✓ Installation verified successfully!"
    exit 0
else
    echo "✗ Found $errors issue(s) - please review"
    exit 1
fi
EOFVERIFY
    chmod +x "$USB_DIR/verify-installation.sh"
    print_step "Created verify-installation.sh"

    # Calculate size
    size=$(du -sh "$USB_DIR" | cut -f1)

    # Print completion message
    print_header "USB Installer Created Successfully!"

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     USB Installer Ready for Deployment                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Location: $USB_DIR"
    echo "Size: $size"
    echo ""
    echo "Next Steps:"
    echo "  1. Copy the mu2-usb folder to a USB drive"
    echo "  2. On each target machine:"
    echo "     a. Copy mu2-usb folder to the machine"
    echo "     b. Run: sudo ./mu2-usb/load-docker-images.sh"
    echo "     c. Run: sudo ./mu2-usb/install.sh"
    echo "     d. Run: ./mu2-usb/verify-installation.sh"
    echo ""
    echo "For fleet deployment (50+ machines):"
    echo "  - Use this USB installer as the master copy"
    echo "  - Duplicate USB drives as needed"
    echo "  - Each install takes approximately 10-15 minutes"
    echo ""
    print_step "USB installer creation completed!"

}

# Run main
main "$@"
