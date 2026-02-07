#!/bin/bash
################################################################################
# Mu2 Cognitive OS - Fleet Health Check Script
# For monitoring health across 50+ deployed Mini-PCs
#
# Usage: ./scripts/health-check-fleet.sh
#
# This script performs a quick health check on the Mu2 Cognitive OS services:
# - Frontend (http://localhost:3000)
# - Backend API (http://localhost:8000)
# - Database (localhost:54322)
#
# Exit Codes:
#   0 = GREEN (All systems operational)
#   1 = YELLOW (Degraded performance)
#   2 = RED (Critical failures)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-54322}"
TIMEOUT="${TIMEOUT:-5}"

# Status tracking
STATUS=0  # 0=GREEN, 1=YELLOW, 2=RED
ISSUES=()

################################################################################
# Helper Functions
################################################################################

print_status() {
    local status=$1
    local message=$2

    case $status in
        GREEN)
            echo -e "${GREEN}[✓]${NC} $message"
            ;;
        YELLOW)
            echo -e "${YELLOW}[!]${NC} $message"
            STATUS=1
            ISSUES+=("$message")
            ;;
        RED)
            echo -e "${RED}[✗]${NC} $message"
            STATUS=2
            ISSUES+=("$message")
            ;;
        *)
            echo -e "${BLUE}[i]${NC} $message"
            ;;
    esac
}

check_service() {
    local name=$1
    local url=$2

    if curl -s -f --max-time "$TIMEOUT" "$url" > /dev/null 2>&1; then
        print_status GREEN "$name is reachable"
        return 0
    else
        print_status RED "$name is NOT reachable"
        return 1
    fi
}

check_database() {
    local host=$1
    local port=$2

    if nc -z -w "$TIMEOUT" "$host" "$port" 2>/dev/null; then
        print_status GREEN "Database is reachable on port $port"
        return 0
    else
        print_status RED "Database is NOT reachable on port $port"
        return 1
    fi
}

check_backend_health() {
    local url=$1

    response=$(curl -s -f --max-time "$TIMEOUT" "$url/health" 2>/dev/null || echo "")

    if [ -n "$response" ]; then
        print_status GREEN "Backend health endpoint responding"
        return 0
    else
        print_status YELLOW "Backend health endpoint not responding (may be starting up)"
        return 1
    fi
}

check_docker_containers() {
    local running_containers=0

    # Check if Mu2 containers are running
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "mu2-postgres"; then
        print_status GREEN "Database container (mu2-postgres) is running"
        running_containers=$((running_containers + 1))
    else
        print_status RED "Database container (mu2-postgres) is NOT running"
    fi

    return $running_containers
}

check_disk_space() {
    local threshold=90  # Alert if disk is >90% full

    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ "$usage" -lt "$threshold" ]; then
        print_status GREEN "Disk space usage: ${usage}%"
    else
        print_status YELLOW "Disk space usage: ${usage}% (threshold: ${threshold}%)"
    fi
}

check_memory() {
    # Simple memory check using free
    if command -v free &> /dev/null; then
        mem_percent=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
        if [ "$mem_percent" -lt 90 ]; then
            print_status GREEN "Memory usage: ${mem_percent}%"
        else
            print_status YELLOW "Memory usage: ${mem_percent}%"
        fi
    fi
}

################################################################################
# Main Health Check
################################################################################

main() {
    # Quiet mode for fleet monitoring (minimal output)
    if [ "${1:-}" = "--quiet" ]; then
        exec 1>/dev/null
        exec 2>/dev/null
    fi

    # Banner (only in verbose mode)
    if [ "${1:-}" != "--quiet" ]; then
        echo ""
        echo "╔═══════════════════════════════════════════════════════════╗"
        echo "║     Mu2 Cognitive OS - Fleet Health Check                 ║"
        echo "╚═══════════════════════════════════════════════════════════╝"
        echo ""
    fi

    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        print_status RED "Docker is not installed"
        exit 2
    fi

    if ! command -v curl &> /dev/null && ! command -v nc &> /dev/null; then
        print_status RED "Neither curl nor nc is available for health checks"
        exit 2
    fi

    # Perform health checks
    check_service "Frontend" "$FRONTEND_URL"
    check_service "Backend API" "$BACKEND_URL"
    check_database "$DB_HOST" "$DB_PORT"
    check_backend_health "$BACKEND_URL"
    check_docker_containers
    check_disk_space
    check_memory

    # Print summary
    if [ "${1:-}" != "--quiet" ]; then
        echo ""
        if [ $STATUS -eq 0 ]; then
            echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║     STATUS: GREEN - All Systems Operational               ║${NC}"
            echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
        elif [ $STATUS -eq 1 ]; then
            echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║     STATUS: YELLOW - Degraded Performance                ║${NC}"
            echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo "Issues detected:"
            for issue in "${ISSUES[@]}"; do
                echo "  • $issue"
            done
        else
            echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║     STATUS: RED - Critical Failures                        ║${NC}"
            echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo "Critical issues detected:"
            for issue in "${ISSUES[@]}"; do
                echo "  • $issue"
            done
        fi
        echo ""
    fi

    exit $STATUS
}

# Run main
main "$@"
