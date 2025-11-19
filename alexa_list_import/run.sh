#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

EMAIL=$(jq -r '.amazon_email' $CONFIG_PATH)
PASSWORD=$(jq -r '.amazon_password' $CONFIG_PATH)
TWOFA=$(jq -r '.amazon_2fa' $CONFIG_PATH)
REGION=$(jq -r '.amazon_region' $CONFIG_PATH)
WEBHOOK=$(jq -r '.webhook_url' $CONFIG_PATH)
INTERVAL=$(jq -r '.polling_interval' $CONFIG_PATH)
CLEAR=$(jq -r '.clear_after_import' $CONFIG_PATH)

echo "Starting Alexa List Import Add-on..."
echo "Region: $REGION, polling: $INTERVAL sec"

python3 /app/app.py \
  --email "$EMAIL" \
  --password "$PASSWORD" \
  --twofa "$TWOFA" \
  --region "$REGION" \
  --webhook "$WEBHOOK" \
  --interval "$INTERVAL" \
  --clear "$CLEAR"
