#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

# Version laden
VERSION=$(grep -E "^version:" /etc/hassio/addons/data/*/config.yaml 2>/dev/null | awk '{print $2}')
echo "[run.sh] Version: ${VERSION}"

echo "[run.sh] Reading options from /data/options.json"

OPTS=$(cat /data/options.json)

AMAZON_EMAIL=$(echo "$OPTS" | jq -r '.amazon_email')
AMAZON_PASSWORD=$(echo "$OPTS" | jq -r '.amazon_password')
AMAZON_2FA=$(echo "$OPTS" | jq -r '.amazon_2fa')
REGION=$(echo "$OPTS" | jq -r '.region')
WEBHOOK=$(echo "$OPTS" | jq -r '.webhook_url')
INTERVAL=$(echo "$OPTS" | jq -r '.interval')
CLEAR=$(echo "$OPTS" | jq -r '.clear_after_import')
DEBUG=$(echo "$OPTS" | jq -r '.debug')

echo "[run.sh]   amazon_email= ${AMAZON_EMAIL}"
echo "[run.sh]   amazon_password= ********"
echo "[run.sh]   amazon_2fa= ${AMAZON_2FA}"
echo "[run.sh]   region= ${REGION}"
echo "[run.sh]   webhook_url= ${WEBHOOK}"
echo "[run.sh]   interval= ${INTERVAL}"
echo "[run.sh]   clear_after_import= ${CLEAR}"
echo "[run.sh]   debug= ${DEBUG}"

# Variablen Exportieren
export AMAZON_EMAIL="${AMAZON_EMAIL}"
export AMAZON_PASSWORD="${AMAZON_PASSWORD}"
export AMAZON_2FA="${AMAZON_2FA}"
export REGION="${REGION}"
export WEBHOOK="${WEBHOOK}"
export INTERVAL="${INTERVAL}"
export CLEAR="${CLEAR}"
export DEBUG="${DEBUG}"
export ADDON_VERSION="${VERSION}"

echo "[run.sh] Starting app.py"
python3 /app/app.py
