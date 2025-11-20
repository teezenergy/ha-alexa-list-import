#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

CONFIG="/data/options.json"

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG)
REGION=$(jq -r '.region // "de"' $CONFIG)
INTERVAL=$(jq -r '.interval // 180' $CONFIG)
CLEAR_AFTER=$(jq -r '.clear_after_import // true' $CONFIG)
DEBUG=$(jq -r '.debug // false' $CONFIG)
WEBHOOK=$(jq -r '.webhook_url' $CONFIG)

echo "[run.sh]   amazon_email= $AMAZON_EMAIL"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR_AFTER"
echo "[run.sh]   debug= $DEBUG"
echo "[run.sh]   webhook_url= $WEBHOOK"

mask() {
    echo "$1" | sed 's/./*/g'
}

if [ "$DEBUG" = "true" ]; then
    echo "[run.sh][DEBUG] amazon_password=$(mask "$AMAZON_PASSWORD")"
    echo "[run.sh][DEBUG] amazon_2fa=$(mask "$AMAZON_2FA")"
fi

while true; do
    echo "[run.sh] Starting app.py at $(date '+%Y-%m-%d %H:%M:%S')"
    /app/venv/bin/python /app/app.py
    echo "[run.sh] app.py exited — waiting $INTERVAL seconds before restart"
    sleep $INTERVAL
done
