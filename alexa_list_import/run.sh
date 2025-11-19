#!/usr/bin/bash

echo "[run.sh] Alexa List Import starting..."

# Version aus config.yaml laden
VERSION=$(grep "^version:" /data/options.json 2>/dev/null | sed 's/.*: "//;s/"//')
echo "[run.sh] Version: ${VERSION}"

echo "[run.sh] Reading options from /data/options.json"

EMAIL=$(jq -r '.amazon_email' /data/options.json)
PASSWORD="********"
TFA=$(jq -r '.amazon_2fa' /data/options.json)
REGION=$(jq -r '.region' /data/options.json)
WEBHOOK=$(jq -r '.webhook_url' /data/options.json)
INTERVAL=$(jq -r '.interval' /data/options.json)
CLEAR=$(jq -r '.clear_after_import' /data/options.json)
DEBUG=$(jq -r '.debug' /data/options.json)

echo "[run.sh]   amazon_email= $EMAIL"
echo "[run.sh]   amazon_password= ********"
echo "[run.sh]   amazon_2fa= $TFA"
echo "[run.sh]   region= $REGION"
echo "[run.sh]   webhook_url= $WEBHOOK"
echo "[run.sh]   interval= $INTERVAL"
echo "[run.sh]   clear_after_import= $CLEAR"
echo "[run.sh]   debug= $DEBUG"

echo "[run.sh] Starting app.py"
python3 /app/app.py
