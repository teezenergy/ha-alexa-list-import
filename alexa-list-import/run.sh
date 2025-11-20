#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

CONFIG_PATH=/data/options.json

AMAZON_EMAIL=$(jq -r '.amazon_email' $CONFIG_PATH)
AMAZON_PASSWORD=$(jq -r '.amazon_password' $CONFIG_PATH)
AMAZON_2FA=$(jq -r '.amazon_2fa' $CONFIG_PATH)
WEBHOOK_URL=$(jq -r '.webhook_url' $CONFIG_PATH)
INTERVAL=$(jq -r '.interval' $CONFIG_PATH)
CLEAR_AFTER_IMPORT=$(jq -r '.clear_after_import' $CONFIG_PATH)
DEBUG=$(jq -r '.debug' $CONFIG_PATH)

echo "[run.sh] Email: $AMAZON_EMAIL"
echo "[run.sh] Region: de"
echo "[run.sh] Interval: $INTERVAL sec"
echo "[run.sh] Clear after import: $CLEAR_AFTER_IMPORT"
echo "[run.sh] Debug: $DEBUG"

exec python3 /app/app.py
