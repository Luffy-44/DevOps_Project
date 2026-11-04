#!/usr/bin/env bash
# ==============================================================================
# Zestora DevOps - Automated GitHub-to-AWS Continuous Synchronization Daemon
# ==============================================================================
set -eo pipefail

APP_DIR="/home/ubuntu/app"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/zestora-deploy.log"

cd "${APP_DIR}" || exit 1

# Fetch latest commits silently from GitHub
git fetch origin main > /dev/null 2>&1

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "${LOCAL_HASH}" != "${REMOTE_HASH}" ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S UTC')
    echo "=================================================================" | tee -a "${LOG_FILE}"
    echo "[${TIMESTAMP}] 🔄 New GitHub commit detected!" | tee -a "${LOG_FILE}"
    echo "  Previous: ${LOCAL_HASH}" | tee -a "${LOG_FILE}"
    echo "  New:      ${REMOTE_HASH}" | tee -a "${LOG_FILE}"
    echo "=================================================================" | tee -a "${LOG_FILE}"

    echo "📥 Updating working directory..." | tee -a "${LOG_FILE}"
    git reset --hard origin/main | tee -a "${LOG_FILE}"

    echo "🐳 Rebuilding containers with new code..." | tee -a "${LOG_FILE}"
    docker compose -f "${COMPOSE_FILE}" up -d --build --remove-orphans | tee -a "${LOG_FILE}"

    echo "🧹 Removing unused images..." | tee -a "${LOG_FILE}"
    docker image prune -f > /dev/null 2>&1 || true

    echo "✅ [$(date '+%Y-%m-%d %H:%M:%S UTC')] Deployment successful!" | tee -a "${LOG_FILE}"
fi
