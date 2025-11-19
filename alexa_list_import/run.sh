#!/bin/sh
set -eu

CONFIG_PATH=/data/options.json

echo "[run.sh] reading options from $CONFIG_PATH"

# Read options (jq must be available in the add-on; Home Assistant base images have it)
EMAIL=$(jq -r '.amazon_email // ""' $CONFIG_PATH)
PASSWORD=$(jq -r '.amazon_password // ""' $CONFIG_PATH)
TWOFA=$(jq -r '.amazon_2fa // ""' $CONFIG_PATH)
REGION=$(jq -r '.amazon_region // "de"' $CONFIG_PATH)
WEBHOOK=$(jq -r '.webhook_url // ""' $CONFIG_PATH)
INTERVAL=$(jq -r '.polling_interval // 60' $CONFIG_PATH)
CLEAR=$(jq -r '.clear_after_import // false' $CONFIG_PATH)
MODE=$(jq -r '.mode // "daemon"' $CONFIG_PATH)  # "daemon" or "oneshot"
DEBUG=$(jq -r '.debug // false' $CONFIG_PATH)

echo "[run.sh] mode=$MODE debug=$DEBUG region=$REGION interval=${INTERVAL}s clear_after_import=$CLEAR"
if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "[run.sh] ERROR: amazon_email or amazon_password is empty. Please set them in the add-on options."
  exit 1
fi

cmd="python3 /app/app.py \
  --email \"$EMAIL\" \
  --password \"$PASSWORD\" \
  --twofa \"$TWOFA\" \
  --region \"$REGION\" \
  --webhook \"$WEBHOOK\" \
  --interval $INTERVAL \
  --clear $CLEAR \
  --mode $MODE \
  --debug $DEBUG"

echo "[run.sh] executing: $cmd"
# exec preserves signals
eval exec $cmd
