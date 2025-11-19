#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

VERSION=$(grep 'version:' /run/config.yaml | awk '{print $2}')
echo "[run.sh] Version: $VERSION"

echo "[run.sh] Reading options from /data/options.json"
CONFIG_PATH=/data/options.json

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG_PATH)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG_PATH)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG_PATH)
REGION=$(jq -r '.region' $CONFIG_PATH)
WEBHOOK_URL=$(jq -r '.webhook_url' $CONFIG_PATH)
INTERVAL=$(jq -r '.interval' $CONFIG_PATH)
CLEAR_AFTER_IMPORT=$(jq -r '.clear_after_import' $CONFIG_PATH)
DEBUG=$(jq -r '.debug' $CONFIG_PATH)

echo "[run.sh]   amazon_email= $AMAZON_EMAIL"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR_AFTER_IMPORT"
echo "[run.sh]   debug= $DEBUG"

echo "[run.sh] Starting app.py"

exec python3 /app/app.py
