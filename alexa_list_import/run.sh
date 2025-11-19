#!/bin/sh
set -eu

echo "[run.sh] Using Python to load /data/options.json"

# Read HA options using Python (no jq needed)
OPTIONS=$(python3 - << 'EOF'
import json
import sys

try:
    with open("/data/options.json") as f:
        cfg = json.load(f)
except:
    print("ERROR: Could not read /data/options.json")
    sys.exit(1)

def get(k, default=""):
    return str(cfg.get(k, default))

print(
    get("amazon_email"), "\n",
    get("amazon_password"), "\n",
    get("amazon_2fa"), "\n",
    get("amazon_region", "de"), "\n",
    get("webhook_url"), "\n",
    get("polling_interval", "60"), "\n",
    get("clear_after_import", "false"), "\n",
    get("mode", "daemon"), "\n",
    get("debug", "false")
)
EOF
)

EMAIL=$(echo "$OPTIONS" | sed -n 1p)
PASSWORD=$(echo "$OPTIONS" | sed -n 2p)
TWOFA=$(echo "$OPTIONS" | sed -n 3p)
REGION=$(echo "$OPTIONS" | sed -n 4p)
WEBHOOK=$(echo "$OPTIONS" | sed -n 5p)
INTERVAL=$(echo "$OPTIONS" | sed -n 6p)
CLEAR=$(echo "$OPTIONS" | sed -n 7p)
MODE=$(echo "$OPTIONS" | sed -n 8p)
DEBUG=$(echo "$OPTIONS" | sed -n 9p)

echo "[run.sh] mode=$MODE debug=$DEBUG region=$REGION interval=${INTERVAL}s clear_after_import=$CLEAR"

exec python3 /app/app.py \
    --email "$EMAIL" \
    --password "$PASSWORD" \
    --twofa "$TWOFA" \
    --region "$REGION" \
    --webhook "$WEBHOOK" \
    --interval "$INTERVAL" \
    --clear "$CLEAR" \
    --mode "$MODE" \
    --debug "$DEBUG"
