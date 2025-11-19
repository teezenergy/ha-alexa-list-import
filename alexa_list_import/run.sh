#!/usr/bin/env bash

echo "[run.sh] Alexa List Import starting..."

# Read version from config.yaml
ADDON_VERSION=$(grep -R "version:" /etc/hassio/addons/data/*/config.yaml 2>/dev/null | head -n1 | awk '{print $2}')
echo "[run.sh] Version: ${ADDON_VERSION}"

echo "[run.sh] Reading options from /data/options.json"

EMAIL=$(jq -r '.amazon_email' /data/options.json)
PASSWORD="********"
TWOFA=$(jq -r '.amazon_2fa' /data/options.json)
REGION=$(jq -r '.region' /data/options.json)
WEBHOOK=$(jq -r '.webhook_url' /data/options.json)
INTERVAL=$(jq -r '.interval' /data/options.json)
CLEAR=$(jq -r '.clear_after_import' /data/options.json)
DEBUG=$(jq -r '.debug' /data/options.json)

echo "[run.sh]   amazon_email= $EMAIL"
echo "[run.sh]   amazon_password= ********"
echo "[run.sh]   amazon_2fa= $TWOFA"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   webhook_url= $WEBHOOK"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR"
echo "[run.sh]   debug= $DEBUG"
echo "[run.sh]   addon_version= $ADDON_VERSION"

echo "[run.sh] Starting app.py"

export ADDON_VERSION

python3 /app/app.py
