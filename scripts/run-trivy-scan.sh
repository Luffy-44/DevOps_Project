#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Zestora – Automated Trivy Security Vulnerability Scanner
#  Scans Dockerfiles, container images, and repository for CVEs and secret leaks.
# ─────────────────────────────────────────────────────────────────────────────

set -e

REPORT_DIR="./reports"
mkdir -p "${REPORT_DIR}"

echo "========================================================"
echo "  🛡️  ZESTORA DEVSECOPS - TRIVY SECURITY SCANNER"
echo "========================================================"

# Check if Trivy is installed; if not, pull Trivy official docker image
if command -v trivy &> /dev/null; then
    TRIVY_CMD="trivy"
else
    echo "ℹ️  Trivy CLI not found locally; executing via Docker (aquasec/trivy:latest)..."
    TRIVY_CMD="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd):/workspace -w /workspace aquasec/trivy:latest"
fi

echo ""
echo "[1/3] 🔍 Scanning Repository Filesystem & IaC Configurations for CVEs and Secrets..."
${TRIVY_CMD} fs --scanners vuln,secret,config \
    --severity HIGH,CRITICAL \
    --format table \
    --output "${REPORT_DIR}/trivy-fs-report.txt" \
    . || true

echo "✅ Filesystem scan completed. Saved to ${REPORT_DIR}/trivy-fs-report.txt"

echo ""
echo "[2/3] 🔍 Scanning Backend Docker Image (zestora_backend)..."
${TRIVY_CMD} image \
    --severity HIGH,CRITICAL \
    --format table \
    --output "${REPORT_DIR}/trivy-backend-report.txt" \
    zestora-backend:latest || true

echo "✅ Backend image scan completed. Saved to ${REPORT_DIR}/trivy-backend-report.txt"

echo ""
echo "[3/3] 🔍 Scanning Frontend Docker Image (zestora_frontend)..."
${TRIVY_CMD} image \
    --severity HIGH,CRITICAL \
    --format table \
    --output "${REPORT_DIR}/trivy-frontend-report.txt" \
    zestora-frontend:latest || true

echo "✅ Frontend image scan completed. Saved to ${REPORT_DIR}/trivy-frontend-report.txt"

echo ""
echo "========================================================"
echo "  🎉 TRIVY SCAN COMPLETE - ALL REPORTS GENERATED!"
echo "  Reports location: ${REPORT_DIR}/"
echo "========================================================"

