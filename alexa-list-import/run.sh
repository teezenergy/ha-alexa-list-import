#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

CONFIG_FILE="/data/options.json"

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG_FILE)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG_FILE)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG_FILE)
REGION=$(jq -r '.region' $CONFIG_FILE)
WEBHOOK_URL=$(jq -r '.webhook_url' $CONFIG_FILE)
INTERVAL=$(jq -r '.interval' $CONFIG_FILE)
CLEAR_AFTER=$(jq -r '.clear_after_import' $CONFIG_FILE)
DEBUG=$(jq -r '.debug' $CONFIG_FILE)

echo "[run.sh]   amazon_email= $AMAZON_EMAIL"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR_AFTER"
echo "[run.sh]   debug= $DEBUG"

# Start Python app
while true; do
    echo "[run.sh] Starting app.py"
    /app/venv/bin/python /app/app.py
    sleep $INTERVAL
done
