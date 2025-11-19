#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

# Version aus config.yaml extrahieren
CONFIG_FILE="/data/options.json"
ADDON_VERSION=$(grep version /etc/hassio/addons/*/alexa_list_import/config.yaml 2>/dev/null | awk -F'"' '{print $2}')

echo "[run.sh] Version: ${ADDON_VERSION}"

echo "[run.sh] Reading options from ${CONFIG_FILE}"

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG_FILE)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG_FILE)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG_FILE)
REGION=$(jq -r '.region' $CONFIG_FILE)
WEBHOOK_URL=$(jq -r '.webhook_url' $CONFIG_FILE)
INTERVAL=$(jq -r '.interval' $CONFIG_FILE)
CLEAR_AFTER_IMPORT=$(jq -r '.clear_after_import' $CONFIG_FILE)
DEBUG=$(jq -r '.debug' $CONFIG_FILE)

echo "[run.sh]   amazon_email= ${AMAZON_EMAIL}"
echo "[run.sh]   region= ${REGION}"
echo "[run.sh]   interval= ${INTERVAL}"
echo "[run.sh]   clear_after_import= ${CLEAR_AFTER_IMPORT}"
echo "[run.sh]   debug= ${DEBUG}"

export AMAZON_EMAIL AMAZON_PASSWORD AMAZON_2FA REGION WEBHOOK_URL INTERVAL CLEAR_AFTER_IMPORT DEBUG ADDON_VERSION

echo "[run.sh] Starting app.py"
python3 /app/app.py
