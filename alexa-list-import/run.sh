#!/usr/bin/ash

echo "[run.sh] Alexa List Import starting..."
echo "[run.sh] Version: 2.0.1"

# Read options.json from Home Assistant
OPTIONS_FILE="/data/options.json"

amazon_email=$(jq -r '.amazon_email' $OPTIONS_FILE)
amazon_password=$(jq -r '.amazon_password' $OPTIONS_FILE)
amazon_2fa=$(jq -r '.amazon_2fa' $OPTIONS_FILE)
webhook_url=$(jq -r '.webhook_url' $OPTIONS_FILE)
region=$(jq -r '.region // "de"' $OPTIONS_FILE)
interval=$(jq -r '.interval // 180' $OPTIONS_FILE)
clear_after_import=$(jq -r '.clear_after_import // true' $OPTIONS_FILE)
debug=$(jq -r '.debug // false' $OPTIONS_FILE)

echo "[run.sh] Reading options from $OPTIONS_FILE"
echo "[run.sh]   amazon_email= $amazon_email"
echo "[run.sh]   region= $region"
echo "[run.sh]   interval= $interval"
echo "[run.sh]   clear_after_import= $clear_after_import"
echo "[run.sh]   debug= $debug"

# Activate Python virtual environment
source /app/venv/bin/activate

# Start Python app
python3 /app/app.py
