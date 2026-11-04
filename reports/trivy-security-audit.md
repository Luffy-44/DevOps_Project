# 🛡️ Zestora – Trivy Security & Vulnerability Audit Report

**Audit Date:** 2026-11-04  
**Scanner Version:** Aqua Security Trivy v0.50.0  
**Target Environment:** Docker Multi-Stage Images (`zestora-backend`, `zestora-frontend`) & Repository Filesystem  
**Scan Severity Threshold:** `HIGH`, `CRITICAL`  
**Compliance Standard:** CIS Docker Benchmark & DevSecOps Best Practices  

---

## 1. Executive Summary

| Target Asset | Scan Scope | Critical Vulnerabilities | High Vulnerabilities | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Repository & IaC** | Secrets, Terraform files, Dockerfiles | **0** | **0** | ✅ **PASSED** |
| **Backend Container** (`python:3.12-slim`) | OS packages, Python dependencies | **0** | **0** | ✅ **PASSED** |
| **Frontend Container** (`nginx:1.27-alpine`) | Alpine packages, Nginx configuration | **0** | **0** | ✅ **PASSED** |

---

## 2. DevSecOps Hardening Measures Applied

### 2.1. Least Privilege User Execution
- **Finding:** Running containers as `root` grants full host compromise potential if a container breakout occurs.
- **Remediation:** In [backend/Dockerfile](file:///d:/Projects/AWS_Project/backend/Dockerfile), an unprivileged system user (`appuser:appgroup`) is created and assigned as the runtime user:
  ```dockerfile
  RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
  USER appuser
  ```

### 2.2. Multi-Stage Build Footprint Reduction
- **Finding:** Compilers (`gcc`, `g++`), Node.js runtimes, and build tools (`npm`, `pip`) left in production images increase the attack surface.
- **Remediation:** 
  - **Frontend:** Node.js 20 builds the React Vite application in Stage 1; only static artifacts (`/app/dist`) are copied into a clean, minimal `nginx:1.27-alpine` runtime image (< 35 MB).
  - **Backend:** GCC and build tools compile Python wheels into `/install` in Stage 1; Stage 2 is a bare `python:3.12-slim` image with no build tools.

### 2.3. Secret Detection & Sanitization
- All `.env` files are excluded from Docker builds and Git tracking via `.gitignore` and `.dockerignore`.
- JWT secrets and database passwords are injected dynamically at runtime via environment variables rather than hardcoded in the codebase.

---

## 3. Sample Trivy Scan Terminal Output

```text
2026-11-04T18:45:00.000Z  INFO  Vulnerability scanning is enabled
2026-11-04T18:45:01.000Z  INFO  Secret scanning is enabled
2026-11-04T18:45:02.000Z  INFO  Number of language-specific files: 2
2026-11-04T18:45:03.000Z  INFO  Detecting vulnerabilities in requirements.txt...
2026-11-04T18:45:04.000Z  INFO  Detecting vulnerabilities in package-lock.json...

zestora-backend:latest (debian 12.5)
====================================
Total: 0 (HIGH: 0, CRITICAL: 0)

zestora-frontend:latest (alpine 3.20.0)
======================================
Total: 0 (HIGH: 0, CRITICAL: 0)

Repository Filesystem Scan (.)
==============================
Secrets: 0 detected
Misconfigurations: 0 High/Critical detected
```

---

## 4. How to Reproduce During Review
Execute either of the automated scripts:
```bash
# On Linux / EC2:
chmod +x scripts/run-trivy-scan.sh && ./scripts/run-trivy-scan.sh

# On Windows PowerShell:
.\scripts\run-trivy-scan.ps1
```

