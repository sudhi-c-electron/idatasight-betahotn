#!/usr/bin/env bash
# Push code changes to the running instance. ~40 seconds.
# Never touches data/ — your live demo state is safe.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.env"
KEYFILE="$HERE/${STACK}-key.pem"
EIP=$(cat "$HERE/.state/eip_ip" 2>/dev/null) || { echo "No deployment found. Run ./deploy/deploy.sh"; exit 1; }
SSH="ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new ubuntu@$EIP"

FRONTEND=0
[ "${1:-}" = "--frontend" ] && FRONTEND=1

echo "→ syncing code (data/ excluded — live demo state preserved)"
rsync -az \
  --exclude '.web' --exclude '.venv' --exclude '__pycache__' --exclude '.states' \
  --exclude 'reflex.lock' --exclude 'data' --exclude 'deploy/.state' --exclude 'deploy/*.pem' \
  -e "ssh -i $KEYFILE -o StrictHostKeyChecking=accept-new" \
  "$APP_DIR/" "ubuntu@$EIP:/home/ubuntu/idatasight/"

if [ "$FRONTEND" = 1 ]; then
  echo "→ rebuilding frontend (2-4 min — only needed for UI changes)"
  $SSH "bash -lc '
    set -e
    cd ~/idatasight && source .venv/bin/activate
    export REFLEX_API_URL=https://$DOMAIN
    export REFLEX_DEPLOY_URL=https://$DOMAIN
    export IDATASIGHT_DEMO=$IDATASIGHT_DEMO IDATASIGHT_SOURCE=$IDATASIGHT_SOURCE
    rm -rf .web/build
    reflex export --frontend-only --no-zip --env prod --no-ssr
    sudo rsync -a --delete .web/build/client/ /var/www/idatasight/
  '"
  # Same guard as deploy.sh — a rebuild that bakes the wrong origin ships a
  # page that renders and never responds.
  $SSH "grep -q 'wss://$DOMAIN/_event' /var/www/idatasight/assets/reflex-env-*.js" 2>/dev/null \
    && echo "  ✓ bundle points at wss://$DOMAIN/_event" \
    || { echo "  ✗ bundle baked the wrong origin — aborting"; exit 1; }
fi

echo "→ restarting backend"
$SSH "sudo systemctl restart idatasight"
sleep 4
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$DOMAIN/ping" || echo 000)
[ "$code" = "200" ] && echo "✓ live → https://$DOMAIN" \
  || echo "! /ping returned $code — $SSH 'sudo journalctl -u idatasight -n 40 --no-pager'"

echo
echo "No flag needed    — you changed the BODY of an event handler, or backend/*.py"
echo "Needs --frontend  — components/, pages/, theme.py, or you added / renamed /"
echo "                    removed a State var, or changed any component structure"
echo "When unsure       — use --frontend. A skipped rebuild serves a stale UI,"
echo "                    which looks like your fix silently didn't work."
