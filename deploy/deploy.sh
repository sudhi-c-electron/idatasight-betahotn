#!/usr/bin/env bash
# iDataSight → EC2 + Caddy, one command.
# Idempotent and resumable: every step records itself in deploy/.state, so a
# failure mid-run costs you only the step that failed. Safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.env"
STATE="$HERE/.state"
KEYFILE="$HERE/${STACK}-key.pem"
mkdir -p "$STATE"

export AWS_PROFILE AWS_DEFAULT_REGION="$REGION"
AWS="aws --profile $AWS_PROFILE --region $REGION"

# ---------- output helpers ----------
c_hd=$'\033[1;38;5;202m'; c_ok=$'\033[0;32m'; c_wn=$'\033[0;33m'
c_er=$'\033[0;31m'; c_dim=$'\033[2m'; c_0=$'\033[0m'
step() { echo; echo "${c_hd}▸ $*${c_0}"; }
ok()   { echo "  ${c_ok}✓${c_0} $*"; }
warn() { echo "  ${c_wn}!${c_0} $*"; }
die()  { echo "  ${c_er}✗ $*${c_0}" >&2; exit 1; }
dim()  { echo "  ${c_dim}$*${c_0}"; }

remember() { printf '%s' "$2" > "$STATE/$1"; }
recall()   { [ -f "$STATE/$1" ] && cat "$STATE/$1" || true; }

# ---------- 0. preflight ----------
step "Preflight"
[ "$DOMAIN" = "hack.yourdomain.com" ] && die "Edit DOMAIN in deploy/config.env first."
command -v aws >/dev/null || die "aws CLI not found."
command -v rsync >/dev/null || die "rsync not found."

CALLER=$($AWS sts get-caller-identity --query Arn --output text 2>/dev/null) \
  || die "AWS credentials for profile '$AWS_PROFILE' are not working.
    Run this in your own terminal (keeps the secret out of this transcript):
      aws configure --profile $AWS_PROFILE"
ok "authenticated as ${CALLER##*/}"
ok "region $REGION · domain $DOMAIN"

# ---------- 1. key pair ----------
step "SSH key pair"
if [ -f "$KEYFILE" ] && $AWS ec2 describe-key-pairs --key-names "$STACK" >/dev/null 2>&1; then
  ok "reusing $STACK"
else
  $AWS ec2 delete-key-pair --key-name "$STACK" >/dev/null 2>&1 || true
  $AWS ec2 create-key-pair --key-name "$STACK" \
    --query KeyMaterial --output text > "$KEYFILE"
  chmod 400 "$KEYFILE"
  ok "created $STACK → deploy/${STACK}-key.pem"
fi

# ---------- 2. security group ----------
step "Security group"
VPC=$($AWS ec2 describe-vpcs --filters Name=isDefault,Values=true \
      --query 'Vpcs[0].VpcId' --output text)
[ "$VPC" = "None" ] && die "No default VPC in $REGION. Create one, or tell me and I'll add VPC creation."

SG=$($AWS ec2 describe-security-groups \
     --filters "Name=group-name,Values=$STACK" "Name=vpc-id,Values=$VPC" \
     --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo None)
if [ "$SG" = "None" ]; then
  SG=$($AWS ec2 create-security-group --group-name "$STACK" \
       --description "iDataSight hackathon" --vpc-id "$VPC" \
       --query GroupId --output text)
  ok "created $SG"
else
  ok "reusing $SG"
fi

MYIP=$(curl -s --max-time 10 https://checkip.amazonaws.com || echo "")
for rule in "22:${MYIP:-0.0.0.0}/32" "80:0.0.0.0/0" "443:0.0.0.0/0"; do
  port="${rule%%:*}"; cidr="${rule#*:}"
  $AWS ec2 authorize-security-group-ingress --group-id "$SG" \
    --protocol tcp --port "$port" --cidr "$cidr" >/dev/null 2>&1 \
    && ok "opened $port from $cidr" || dim "port $port already open"
done
warn "3000/8000 deliberately closed — Caddy reaches them over loopback"
remember sg "$SG"

# ---------- 3. instance ----------
step "EC2 instance"
IID=$(recall instance)
if [ -n "$IID" ] && \
   [ "$($AWS ec2 describe-instances --instance-ids "$IID" \
        --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)" = "running" ]; then
  ok "reusing $IID"
else
  AMI=$($AWS ssm get-parameters \
    --names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
    --query 'Parameters[0].Value' --output text)
  ok "Ubuntu 24.04 → $AMI"
  IID=$($AWS ec2 run-instances \
    --image-id "$AMI" --instance-type "$INSTANCE_TYPE" \
    --key-name "$STACK" --security-group-ids "$SG" \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$VOLUME_GB,VolumeType=gp3}" \
    --user-data "file://$HERE/user-data.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$STACK}]" \
    --query 'Instances[0].InstanceId' --output text)
  remember instance "$IID"
  ok "launched $IID ($INSTANCE_TYPE) — bootstrapping in background"
  $AWS ec2 wait instance-running --instance-ids "$IID"
fi

# ---------- 4. elastic IP ----------
step "Elastic IP"
EIP=$(recall eip_ip)
if [ -z "$EIP" ]; then
  ALLOC=$($AWS ec2 allocate-address --domain vpc --query AllocationId --output text)
  $AWS ec2 associate-address --instance-id "$IID" --allocation-id "$ALLOC" >/dev/null
  EIP=$($AWS ec2 describe-addresses --allocation-ids "$ALLOC" \
        --query 'Addresses[0].PublicIp' --output text)
  remember eip_alloc "$ALLOC"; remember eip_ip "$EIP"
  ok "allocated + associated $EIP"
else
  ok "reusing $EIP"
fi

# ---------- 5. DNS gate ----------
step "DNS"
echo
echo "  ${c_hd}Create this A record at your DNS provider now:${c_0}"
echo "      Type   A"
echo "      Name   ${DOMAIN%%.*}"
echo "      Value  $EIP"
echo "      TTL    600      (GoDaddy rejects anything below 600)"
echo "      Proxy  DNS only (no Cloudflare orange cloud)"
echo
echo "  Name is the label ONLY — '${DOMAIN%%.*}', not the full hostname,"
echo "  and not '@${DOMAIN%%.*}'. '@' alone means the apex domain."
echo
if [ "$(dig +short "$DOMAIN" 2>/dev/null | tail -1)" = "$EIP" ]; then
  ok "already resolving"
else
  echo -n "  waiting for $DOMAIN → $EIP "
  for i in $(seq 1 300); do
    [ "$(dig +short "$DOMAIN" 2>/dev/null | tail -1)" = "$EIP" ] && { echo; ok "resolving"; break; }
    # Catch the classic GoDaddy mistake early rather than burning the full timeout.
    if [ -n "$(dig +short "$DOMAIN.${DOMAIN#*.}" 2>/dev/null)" ]; then
      echo; die "found $DOMAIN.${DOMAIN#*.} — the Name field got the full hostname.
    Use just '${DOMAIN%%.*}' as the Name, then re-run."
    fi
    [ "$i" = 300 ] && { echo; die "still not resolving after 25 min. Fix the record and re-run — nothing is lost."; }
    sleep 5; echo -n "."
  done
fi

# ---------- 6. wait for bootstrap ----------
step "Instance bootstrap"
SSH="ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 ubuntu@$EIP"
echo -n "  waiting for SSH "
for i in $(seq 1 60); do
  $SSH true 2>/dev/null && { echo; ok "ssh up"; break; }
  [ "$i" = 60 ] && { echo; die "no SSH after 5 min"; }
  sleep 5; echo -n "."
done
echo -n "  waiting for apt/caddy/uv bootstrap "
for i in $(seq 1 96); do
  $SSH 'test -f /opt/bootstrap-done' 2>/dev/null && { echo; ok "bootstrap complete"; break; }
  [ "$i" = 96 ] && { echo; die "bootstrap stalled — check /var/log/idatasight-bootstrap.log on the box"; }
  sleep 5; echo -n "."
done

# ---------- 7. ship code ----------
step "Sync code"
dim "excluding .web (217 MB macOS build), .venv, .states, reflex.lock — all rebuilt on Linux"
# No --info=: macOS ships openrsync / rsync 2.6.9, which predates that flag.
rsync -az \
  --exclude '.web' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.states' --exclude 'reflex.lock' --exclude 'deploy/.state' \
  --exclude 'deploy/*.pem' \
  -e "ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new" \
  "$APP_DIR/" "ubuntu@$EIP:/home/ubuntu/idatasight/"
ok "code + data/ on the box"

# ---------- 8. build ----------
step "Python env + frontend build"
# REFLEX_API_URL — not API_URL. Verified against reflex 0.9.8: the env-var prefix
# is REFLEX_, and the value is compiled into .web/build/client/assets/reflex-env-*.js
# as the websocket origin. Set it wrong and the page renders but never responds.
warn "REFLEX_API_URL is compiled into the bundle — the step that must not be wrong"
dim "first build downloads bun and compiles: 2-4 minutes"
$SSH "bash -lc '
  set -e
  cd ~/idatasight
  export PATH=\$HOME/.local/bin:\$PATH
  [ -d .venv ] || uv venv --python 3.12
  source .venv/bin/activate
  uv pip install -q \"reflex>=0.9.8\"
  export REFLEX_API_URL=https://$DOMAIN
  export REFLEX_DEPLOY_URL=https://$DOMAIN
  export IDATASIGHT_DEMO=$IDATASIGHT_DEMO
  export IDATASIGHT_SOURCE=$IDATASIGHT_SOURCE
  rm -rf .web/build
  timeout 900 reflex export --frontend-only --no-zip --env prod --no-ssr
  sudo mkdir -p /var/www/idatasight
  sudo rsync -a --delete .web/build/client/ /var/www/idatasight/
'" || die "frontend build failed — re-run this script, it resumes here"

# Prove the right origin got baked in, rather than trusting it. This single check
# is what stands between you and a page that renders perfectly and never responds.
if $SSH "grep -q 'wss://$DOMAIN/_event' /var/www/idatasight/assets/reflex-env-*.js" 2>/dev/null; then
  ok "bundle points at wss://$DOMAIN/_event"
else
  die "bundle baked the wrong websocket origin (expected wss://$DOMAIN/_event).
    Check REFLEX_API_URL — note the REFLEX_ prefix; plain API_URL is silently ignored."
fi

# ---------- 9. caddy ----------
step "Caddy"
# Caddy serves the static SPA itself — no Node process at runtime, so restarts are
# instant. The export is a true SPA (index.html only, no per-route HTML), hence the
# try_files fallback so deep links like /beliefs resolve.
$SSH "sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
$DOMAIN {
    encode zstd gzip

    @backend path /_event* /ping /_upload* /_health /_all_routes /auth-codespace
    handle @backend {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        root * /var/www/idatasight
        try_files {path} {path}/index.html {path}.html /index.html
        file_server {
            precompressed gzip
        }
    }
}
EOF
sudo systemctl reload caddy"
ok "static SPA served by Caddy, backend paths proxied, TLS cert requested"

# ---------- 10. systemd ----------
step "systemd service"
$SSH "sudo tee /etc/systemd/system/idatasight.service >/dev/null <<'EOF'
[Unit]
Description=iDataSight (Reflex)
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/idatasight
Environment=\"PATH=/home/ubuntu/idatasight/.venv/bin:/usr/bin:/bin\"
Environment=\"REFLEX_API_URL=https://$DOMAIN\"
Environment=\"REFLEX_DEPLOY_URL=https://$DOMAIN\"
Environment=\"IDATASIGHT_DEMO=$IDATASIGHT_DEMO\"
Environment=\"IDATASIGHT_SOURCE=$IDATASIGHT_SOURCE\"
Environment=\"EVEROS_DATA_DIR=/home/ubuntu/idatasight/data/everos\"
ExecStart=/home/ubuntu/idatasight/.venv/bin/reflex run --env prod --backend-only --backend-host 0.0.0.0 --backend-port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
mkdir -p /home/ubuntu/idatasight/data/everos
sudo systemctl daemon-reload
sudo systemctl enable --now idatasight
sudo systemctl restart idatasight"
ok "service enabled — survives reboot and your laptop closing"

# ---------- 11. verify ----------
step "Verify"
echo -n "  waiting for app "
HEALTHY=0
for i in $(seq 1 60); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "https://$DOMAIN/ping" 2>/dev/null)" = "200" ]; then
    echo; HEALTHY=1; break
  fi
  sleep 5; echo -n "."
done

echo
if [ "$HEALTHY" = 1 ]; then
  ok "https://$DOMAIN/ping → 200"
  ok "TLS certificate issued"
  echo
  echo "  ${c_ok}${c_hd}LIVE → https://$DOMAIN${c_0}"
  echo
  echo "  Confirm the websocket before you trust it:"
  echo "    open https://$DOMAIN, DevTools → Network → WS filter"
  echo "    you need a /_event connection with status 101"
  $SSH "cd ~/idatasight && tar czf ~/data-backup.tgz data" 2>/dev/null \
    && dim "demo-state snapshot saved to ~/data-backup.tgz on the instance"
else
  warn "not healthy yet. Most likely the TLS cert is still being issued."
  echo "    ssh -i deploy/${STACK}-key.pem ubuntu@$EIP"
  echo "    sudo journalctl -u caddy -n 40 --no-pager"
  echo "    sudo journalctl -u idatasight -n 40 --no-pager"
fi

echo
dim "instance $IID · elastic ip $EIP · ~\$0.05/hr"
dim "teardown when done:  ./deploy/teardown.sh"
