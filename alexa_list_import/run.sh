#!/usr/bin/env bash
set -e

echo "[run.sh] Alexa List Import starting..."

# Version aus config.yaml holen
VERSION=$(grep -E "^version:" /etc/hassio/addons/data/*/config.yaml | awk '{print $2}' || true)
echo "[run.sh] Version: $VERSION"

echo "[run.sh] Reading options from /data/options.json"

# Python verwenden, falls jq fehlt (bei dir war jq nicht vorhanden)
eval "$(python3 << 'EOF'
import json
opts = json.load(open('/data/options.json'))
for k, v in opts.items():
    if k == "amazon_password":
        print(f'{k}= ********')
    else:
        print(f'{k}= {v}')
EOF
)"

# Optionen für app.py übergeben
export AMAZON_EMAIL=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["amazon_email"])
EOF
)

export AMAZON_PASSWORD=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["amazon_password"])
EOF
)

export AMAZON_2FA=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["amazon_2fa"])
EOF
)

export REGION=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["region"])
EOF
)

export WEBHOOK=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["webhook_url"])
EOF
)

export INTERVAL=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["interval"])
EOF
)

export CLEAR=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["clear_after_import"])
EOF
)

export DEBUG=$(python3 - <<EOF
import json; print(json.load(open('/data/options.json'))["debug"])
EOF
)

export ADDON_VERSION=$VERSION

echo "[run.sh] Starting app.py"
python3 /app/app.py
