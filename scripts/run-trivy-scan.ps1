# ─────────────────────────────────────────────────────────────────────────────
#  Zestora – Windows PowerShell Trivy Security Vulnerability Scanner
# ─────────────────────────────────────────────────────────────────────────────

$ReportDir = "./reports"
if (!(Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir | Out-Null
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🛡️  ZESTORA DEVSECOPS - TRIVY SECURITY SCANNER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Use Trivy via Docker container on Windows
$TrivyDocker = "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${PWD}:/workspace -w /workspace aquasec/trivy:latest"

Write-Host "`n[1/3] 🔍 Scanning Repository for Secrets, Configs, and Vulnerabilities..." -ForegroundColor Yellow
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${PWD}:/workspace -w /workspace aquasec/trivy:latest fs --scanners vuln,secret,config --severity HIGH,CRITICAL .

Write-Host "`n[2/3] 🔍 Scanning Backend Docker Image..." -ForegroundColor Yellow
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity HIGH,CRITICAL zestora-backend:latest

Write-Host "`n[3/3] 🔍 Scanning Frontend Docker Image..." -ForegroundColor Yellow
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity HIGH,CRITICAL zestora-frontend:latest

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  ✅ TRIVY SECURITY SCAN FINISHED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green

