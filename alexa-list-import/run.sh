#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

CONFIG_FILE="/data/options.json"

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG_FILE)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG_FILE)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG_FILE)
REGION=$(jq -r '.region // "de"' $CONFIG_FILE)
WEBHOOK_URL=$(jq -r '.webhook_url' $CONFIG_FILE)
INTERVAL=$(jq -r '.interval // 180' $CONFIG_FILE)
CLEAR_AFTER=$(jq -r '.clear_after_import // true' $CONFIG_FILE)
DEBUG=$(jq -r '.debug // false' $CONFIG_FILE)

echo "[run.sh]   amazon_email= $AMAZON_EMAIL"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR_AFTER"
echo "[run.sh]   debug= $DEBUG"
echo "[run.sh]   webhook_url= $WEBHOOK_URL"

if [ "$DEBUG" = "true" ]; then
    echo "[run.sh][DEBUG] amazon_password= $AMAZON_PASSWORD"
    echo "[run.sh][DEBUG] amazon_2fa= $AMAZON_2FA"
fi

# Start Python app in a loop (HA expects this)
while true; do
    echo "[run.sh] Starting app.py at $(date '+%Y-%m-%d %H:%M:%S')"
    /app/venv/bin/python /app/app.py
    echo "[run.sh] app.py exited — waiting $INTERVAL seconds before restart"
    sleep $INTERVAL
done
