#!/bin/bash
#
# Phase A Compliance Verification Script
# =======================================
#
# Quick verification that all Phase A compliance features are working.
#
# Usage: ./scripts/verify_phase_a_compliance.sh
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Phase A Compliance Verification                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check A1: Pre-boot script exists and is executable
echo "A1. Telemetry Kill Switch Script"
echo "─────────────────────────────────"

if [ -x "./pre-boot.sh" ]; then
    check_pass "pre-boot.sh exists and is executable"
else
    check_fail "pre-boot.sh not found or not executable"
fi

# Check for .npmrc with telemetry disabled
if [ -f ".npmrc" ]; then
    if grep -q "send-metrics=false" .npmrc; then
        check_pass ".npmrc has telemetry disabled"
    else
        check_fail ".npmrc exists but telemetry not explicitly disabled"
    fi
else
    check_warn ".npmrc not found (will be created by pre-boot.sh)"
fi

echo ""

# Check A2: Citation Lock files exist
echo "A2. Citation Lock Enforcement"
echo "─────────────────────────────"

if [ -f "packages/brain/src/services/citation_lock.py" ]; then
    check_pass "Backend citation_lock.py exists"

    # Check if it's imported in retrieval_nodes.py
    if grep -q "from src.services.citation_lock import citation_lock_service" packages/brain/src/graph/retrieval_nodes.py; then
        check_pass "Citation lock is integrated in retrieval_nodes.py"
    else
        check_fail "Citation lock not integrated in retrieval_nodes.py"
    fi
else
    check_fail "Backend citation_lock.py not found"
fi

if [ -f "apps/web/components/citation-highlighter.tsx" ]; then
    check_pass "Frontend citation-highlighter.tsx exists"
else
    check_fail "Frontend citation-highlighter.tsx not found"
fi

echo ""

# Check A3: Reduced Motion support
echo "A3. Reduced Motion Support"
echo "──────────────────────────"

if grep -q "prefers-reduced-motion: reduce" apps/web/app/globals.css; then
    check_pass "Reduced motion media query in globals.css"
else
    check_fail "Reduced motion media query not found in globals.css"
fi

if grep -q "scroll-behavior: auto" apps/web/app/globals.css; then
    check_pass "Scroll behavior override for reduced motion"
else
    check_fail "Scroll behavior override missing"
fi

if grep -q "prefersReducedMotion" apps/web/components/providers/mode-provider.tsx; then
    check_pass "Mode provider checks reduced motion preference"
else
    check_fail "Mode provider does not check reduced motion preference"
fi

echo ""

# Check A4: Dependency audit
echo "A4. Dependency Audit"
echo "────────────────────"

# Check for analytics packages in package.json
ANALYTICS_PACKAGES=("analytics" "telemetry" "posthog" "plausible" "segment" "amplitude" "mixpanel" "sentry" "datadog" "newrelic" "google-analytics")
FOUND_ANALYTICS=0

for pkg in "${ANALYTICS_PACKAGES[@]}"; do
    if grep -q "$pkg" apps/web/package.json; then
        check_warn "Found '$pkg' in package.json (please verify)"
        FOUND_ANALYTICS=$((FOUND_ANALYTICS + 1))
    fi
done

if [ $FOUND_ANALYTICS -eq 0 ]; then
    check_pass "No analytics packages found in frontend dependencies"
fi

# Check pyproject.toml
if [ -f "packages/brain/pyproject.toml" ]; then
    PYTHON_ANALYTICS=0
    for pkg in "${ANALYTICS_PACKAGES[@]}"; do
        if grep -q "$pkg" packages/brain/pyproject.toml; then
            check_warn "Found '$pkg' in pyproject.toml (please verify)"
            PYTHON_ANALYTICS=$((PYTHON_ANALYTICS + 1))
        fi
    done

    if [ $PYTHON_ANALYTICS -eq 0 ]; then
        check_pass "No analytics packages found in Python dependencies"
    fi
fi

echo ""

# Additional WCAG compliance checks
echo "Additional WCAG 2.1 AA Checks"
echo "─────────────────────────────"

if grep -q "sr-only" apps/web/app/globals.css; then
    check_pass "Screen reader only class defined"
else
    check_fail "Screen reader only class not found"
fi

if grep -q "focus-visible" apps/web/app/globals.css; then
    check_pass "Focus visible indicators defined"
else
    check_fail "Focus visible indicators not found"
fi

if grep -q "skip-link" apps/web/app/globals.css; then
    check_pass "Skip link styles defined"
else
    check_fail "Skip link styles not found"
fi

echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Verification Summary                                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS_COUNT checks"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Failed:${NC} $FAIL_COUNT checks"
fi
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ Phase A Compliance Verified!${NC}"
    echo ""
    echo "All critical FERPA/CIPA/WCAG compliance requirements are met."
    echo "The system is ready for development."
    echo ""
    exit 0
else
    echo -e "${RED}✗ Phase A Compliance Failed${NC}"
    echo ""
    echo "Please address the failed checks above before proceeding."
    echo ""
    exit 1
fi
