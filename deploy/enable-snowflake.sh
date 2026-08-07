#!/usr/bin/env bash
# Phase 2: swap the CSV mirror for live Snowflake, using key-pair auth.
#
# Why key-pair: warehouse.py:234 calls connect(connection_name="MN74135"), which
# reads ~/.snowflake/connections.toml. Your local profile uses browser OAuth —
# there is no browser on a server, so that connect throws, and warehouse.py:250
# swallows the exception and silently serves CSV. Key-pair auth is the headless
# replacement. Run this only once the CSV deployment is confirmed working.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.env"
KEYFILE="$HERE/${STACK}-key.pem"
EIP=$(cat "$HERE/.state/eip_ip" 2>/dev/null) || { echo "No deployment found."; exit 1; }
SSH="ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new ubuntu@$EIP"

echo "Snowflake connection details (from Snowsight → account menu → Copy account identifier)"
read -rp "  account identifier (ORGNAME-ACCOUNTNAME) : " SF_ACCOUNT
read -rp "  user                                    : " SF_USER
read -rp "  role                                    : " SF_ROLE
read -rp "  warehouse                               : " SF_WH

# ---------- 1. key pair ----------
if [ ! -f "$HERE/rsa_key.p8" ]; then
  echo "→ generating RSA key pair"
  openssl genrsa 2048 2>/dev/null | openssl pkcs8 -topk8 -inform PEM -out "$HERE/rsa_key.p8" -nocrypt
  openssl rsa -in "$HERE/rsa_key.p8" -pubout -out "$HERE/rsa_key.pub" 2>/dev/null
  chmod 400 "$HERE/rsa_key.p8"
fi

PUB=$(sed -e '1d' -e '$d' "$HERE/rsa_key.pub" | tr -d '\n')
echo
echo "════════════════════════════════════════════════════════════════"
echo " Run this in Snowsight as ACCOUNTADMIN or SECURITYADMIN, then"
echo " come back and press Enter:"
echo
echo "   ALTER USER $SF_USER SET RSA_PUBLIC_KEY='$PUB';"
echo "════════════════════════════════════════════════════════════════"
read -rp "Pressed Enter once that statement succeeded: " _

# ---------- 2. install on the server ----------
echo "→ installing connector and credentials"
$SSH "bash -lc '
  cd ~/idatasight && source .venv/bin/activate
  uv pip install -q snowflake-connector-python
  mkdir -p ~/.snowflake && chmod 700 ~/.snowflake
'"
scp -q -i "$KEYFILE" "$HERE/rsa_key.p8" "ubuntu@$EIP:/home/ubuntu/.snowflake/rsa_key.p8"
$SSH "chmod 400 ~/.snowflake/rsa_key.p8"

# Profile name must stay MN74135 — that is the default SF_CONNECTION in warehouse.py:22
$SSH "cat > ~/.snowflake/connections.toml <<'EOF'
[MN74135]
account = \"$SF_ACCOUNT\"
user = \"$SF_USER\"
role = \"$SF_ROLE\"
warehouse = \"$SF_WH\"
database = \"BETATHON\"
schema = \"RAW\"
authenticator = \"SNOWFLAKE_JWT\"
private_key_file = \"/home/ubuntu/.snowflake/rsa_key.p8\"
EOF
chmod 600 ~/.snowflake/connections.toml"

# ---------- 3. flip the source ----------
echo "→ switching IDATASIGHT_SOURCE to snowflake"
$SSH "sudo sed -i 's/IDATASIGHT_SOURCE=csv/IDATASIGHT_SOURCE=snowflake/' \
        /etc/systemd/system/idatasight.service
      sudo systemctl daemon-reload && sudo systemctl restart idatasight"
sleep 8

# ---------- 4. verify it ACTUALLY connected ----------
# The UI looks identical either way, so the log is the only honest signal.
echo "→ checking whether it really connected"
FAIL=$($SSH "sudo journalctl -u idatasight --since '2 min ago' --no-pager | grep -i 'snowflake read failed' || true")
echo
if [ -z "$FAIL" ]; then
  echo "✓ live Snowflake — no fallback messages in the log"
  sed -i.bak 's/IDATASIGHT_SOURCE="csv"/IDATASIGHT_SOURCE="snowflake"/' "$HERE/config.env" && rm -f "$HERE/config.env.bak"
else
  echo "✗ still falling back to CSV. The app works, but is NOT using Snowflake:"
  echo "$FAIL" | head -5
  echo
  echo "Usual causes, in order of likelihood:"
  echo "  · the ALTER USER statement did not run, or ran against a different user"
  echo "  · a network policy IP allowlist is blocking $EIP"
  echo "    → Snowsight → Admin → Security → Network policies, add $EIP"
  echo "  · role cannot read BETATHON.RAW"
  echo
  echo "Roll back to CSV any time:"
  echo "  ssh -i deploy/${STACK}-key.pem ubuntu@$EIP \\"
  echo "    \"sudo sed -i 's/SOURCE=snowflake/SOURCE=csv/' /etc/systemd/system/idatasight.service &&"
  echo "     sudo systemctl daemon-reload && sudo systemctl restart idatasight\""
fi
