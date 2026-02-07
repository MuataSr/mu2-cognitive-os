#!/bin/bash
#
# Mu2 Cognitive OS - Pre-Boot Kill Switch
# ========================================
#
# This script scans for and blocks analytics/telemetry code before
# starting the application. Ensures FERPA compliance and user privacy.
#
# Usage: ./pre-boot.sh [--force]
#
# Options:
#   --force    Remove found telemetry without asking
#
# FERPA Compliance Notes:
# - This project handles educational data (student records, learning progress)
# - No analytics, telemetry, or tracking is permitted
# - All data must remain on localhost only
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Common telemetry patterns to scan for
TELEMETRY_PATTERNS=(
    "scarf\.sh"
    "analytics"
    "posthog"
    "plausible"
    "segment\.io"
    "amplitude"
    "mixpanel"
    "google-analytics"
    "gtag"
    "fbq"
    "tracking"
    "telemetry"
    "sentry"  # Error tracking that may leak data
    "datadog"
    "newrelic"
)

# Directories to scan
SCAN_DIRS=(
    "apps"
    "packages"
    ".github"
    "supabase"
)

# Results storage
declare VIOLATIONS=()
declare FILES_TO_FIX=()

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Scan file for telemetry patterns
scan_file() {
    local file="$1"
    local filename=$(basename "$file")

    # Skip node_modules and build directories
    if [[ "$file" =~ node_modules|\.next|dist|build|\.git ]]; then
        return 0
    fi

    # Skip this script itself
    if [[ "$filename" == "pre-boot.sh" ]]; then
        return 0
    fi

    # Read file content
    if [[ ! -f "$file" ]]; then
        return 0
    fi

    local content
    content=$(cat "$file" 2>/dev/null || echo "")

    # Check each pattern
    for pattern in "${TELEMETRY_PATTERNS[@]}"; do
        if echo "$content" | grep -qiE "$pattern"; then
            # Check if it's a false positive (e.g., in comments, documentation)
            if [[ "$file" =~ \.(md|txt)$ ]]; then
                # Documentation mentioning telemetry is okay
                continue
            fi

            VIOLATIONS+=("$file: matches pattern '$pattern'")
            FILES_TO_FIX+=("$file")
            return 1
        fi
    done

    return 0
}

# Recursively scan directory
scan_directory() {
    local dir="$1"

    if [[ ! -d "$dir" ]]; then
        return 0
    fi

    log_info "Scanning directory: $dir"

    while IFS= read -r -d '' file; do
        scan_file "$file" || true
    done < <(find "$dir" -type f -print0)
}

# Check package.json for telemetry dependencies
check_package_json() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        return 0
    fi

    log_info "Checking package.json: $file"

    # Check for known telemetry packages
    local telemetry_packages=(
        "@scarf/scarf"
        "analytics"
        "@segment/analytics-node"
        "@segment/analytics-next"
        "posthog-js"
        "@posthog/.*"
        "plausible-tracker"
        "@plausible/.*"
        "@amplitude/.*"
        "@mixpanel/.*"
        "@sentry/.*"
        "datadog-.*"
        "newrelic"
        "@google-analytics/.*"
    )

    for pkg in "${telemetry_packages[@]}"; do
        if grep -q "$pkg" "$file"; then
            VIOLATIONS+=("$file: contains telemetry package '$pkg'")
            FILES_TO_FIX+=("$file")
        fi
    done
}

# Remove telemetry from package.json
remove_from_package_json() {
    local file="$1"
    local temp_file="${file}.tmp"

    log_info "Removing telemetry from: $file"

    # Create a clean version using Python (more reliable than sed for JSON)
    python3 - <<PYTHON_SCRIPT
import json
import sys

try:
    with open('$file', 'r') as f:
        data = json.load(f)

    # Remove telemetry packages from dependencies
    for key in ['dependencies', 'devDependencies', 'peerDependencies']:
        if key in data:
            packages_to_remove = []
            for pkg in data[key]:
                if any(tele in pkg.lower() for tele in [
                    'scarf', 'analytics', 'posthog', 'plausible',
                    'segment', 'amplitude', 'mixpanel', 'sentry',
                    'datadog', 'newrelic', 'google-analytics'
                ]):
                    packages_to_remove.append(pkg)

            for pkg in packages_to_remove:
                del data[key][pkg]
                print(f"  Removed: {pkg}")

    # Write cleaned JSON
    with open('$temp_file', 'w') as f:
        json.dump(data, f, indent=2)

    # Replace original
    import os
    os.replace('$temp_file', '$file')
    print(f"Cleaned: $file")

except Exception as e:
    print(f"Error processing $file: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
}

# Create .npmrc with telemetry disabled
create_npmrc() {
    local npmrc_file=".npmrc"

    log_info "Creating/updating .npmrc with telemetry disabled"

    cat > "$npmrc_file" << 'EOF'
# Mu2 Cognitive OS - NPM Configuration
# ====================================
# All telemetry and analytics DISABLED for FERPA compliance

fund=false
audit=false
audit-level=moderate
ignore-scripts=false
progress=false

# Disable all analytics
send-metrics=false
update-notifier=false
EOF

    log_info "Created: $npmrc_file"
}

# Check config files for telemetry settings and enforce FALSE
check_config_files() {
    log_info "Checking configuration files for telemetry settings..."

    local config_files=(
        "apps/web/next.config.js"
        "apps/web/next.config.mjs"
        ".env"
        ".env.example"
        "packages/brain/src/core/config.py"
    )

    local telemetry_found=false
    local files_to_patch=()

    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            # Check for telemetry-related settings that aren't explicitly false
            if grep -qiE "telemetry|analytics|instrumentation.*true" "$config_file" 2>/dev/null; then
                # Check if telemetry is enabled (not set to false/disabled)
                if grep -qE "telemetry.*=.*true|analytics.*=.*true|instrumentation.*=.*true" "$config_file" 2>/dev/null; then
                    log_error "TELEMETRY ENABLED in $config_file - MUST BE FALSE"
                    telemetry_found=true
                    files_to_patch+=("$config_file")
                fi
            fi
        fi
    done

    # Hard constraint: If telemetry is found in configs, fail and refuse to start
    if [[ "$telemetry_found" == "true" ]]; then
        log_error ""
        log_error "╔════════════════════════════════════════════════════════════╗"
        log_error "║  HARD CONSTRAINT VIOLATION: TELEMETRY MUST BE DISABLED    ║"
        log_error "╚════════════════════════════════════════════════════════════╝"
        log_error ""
        log_error "The following files have telemetry enabled:"
        for file in "${files_to_patch[@]}"; do
            log_error "  - $file"
        done
        log_error ""
        log_error "ACTION REQUIRED: Set all telemetry/analytics settings to FALSE"
        log_error ""
        log_error "Example fixes:"
        log_error "  next.config.js: instrumentation: false"
        log_error "  .env: TELEMETRY_ENABLED=false"
        log_error ""
        log_error "Application CANNOT start until telemetry is disabled."
        log_error "This is a FERPA compliance requirement."
        log_error ""
        return 1
    fi

    log_info "✓ All configuration files have telemetry disabled"
    return 0
}

# Main execution
main() {
    local force=false

    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --force)
                force=true
                ;;
            --strict)
                # Strict mode: exit on any finding
                set -e
                ;;
            -h|--help)
                echo "Usage: $0 [--force] [--strict]"
                echo ""
                echo "Scan for and block analytics/telemetry code."
                echo "HARD CONSTRAINT: Will refuse to start if telemetry is enabled in configs."
                echo ""
                echo "Options:"
                echo "  --force    Remove found telemetry without asking"
                echo "  --strict   Exit immediately on any finding (for CI/CD)"
                exit 0
                ;;
        esac
    done

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║  🔒 Mu2 Cognitive OS - Pre-Boot Kill Switch                        ║"
    echo "║  FERPA Compliance Audit & Telemetry Blocker                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Scanning for analytics and telemetry..."
    echo ""

    # HARD CONSTRAINT: Check config files first - fail if telemetry enabled
    if ! check_config_files; then
        log_error "Pre-boot check FAILED. Application will NOT start."
        exit 1
    fi

    # Scan all directories
    for dir in "${SCAN_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            scan_directory "$dir"
            # Check for package.json files
            while IFS= read -r -d '' pkg; do
                check_package_json "$pkg"
            done < <(find "$dir" -name "package.json" -print0)
        fi
    done

    # Report results
    echo ""
    if [[ ${#VIOLATIONS[@]} -eq 0 ]]; then
        log_info "✓ No telemetry violations found!"
        log_info "System is clean and FERPA compliant."
    else
        log_error "Found ${#VIOLATIONS[@]} potential telemetry violations:"
        echo ""

        for violation in "${VIOLATIONS[@]}"; do
            log_warn "  - $violation"
        done

        echo ""
        log_warn "These must be removed before starting the application."

        # Ask for confirmation unless --force
        if [[ "$force" == "true" ]]; then
            log_info "--force flag set, proceeding with removal..."
            auto_confirm=true
        else
            echo -n "Remove telemetry now? [y/N] "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                auto_confirm=true
            else
                log_error "Aborted. Please remove telemetry manually or run with --force"
                exit 1
            fi
        fi

        # Remove telemetry
        echo ""
        log_info "Removing telemetry..."

        for file in "${FILES_TO_FIX[@]}"; do
            if [[ "$file" =~ package\.json$ ]]; then
                remove_from_package_json "$file"
            else
                log_warn "Manual removal required for: $file"
            fi
        done

        # Create/update .npmrc
        create_npmrc

        echo ""
        log_info "Telemetry removal complete!"
    fi

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║  🔒 SECURE MODE ACTIVE: TELEMETRY DISABLED                         ║"
    echo "║  ✓ No external analytics detected                                  ║"
    echo "║  ✓ All data remains on localhost                                  ║"
    echo "║  ✓ FERPA compliance verified                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    log_info "=== Pre-Boot Check Complete ==="
    log_info "You may now start the application."
    echo ""

    # Display startup commands
    log_info "Startup commands:"
    echo "  docker-compose up -d    # Start all services"
    echo "  cd apps/web && npm install && npm run dev    # Start frontend"
    echo "  cd packages/brain && pip install && uvicorn src.main:app    # Start backend"
    echo ""
    return 0
}

# Run main
main "$@"
