#!/usr/bin/env bash
# Destroy everything deploy.sh created. Pulls your demo state down first.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.env"
STATE="$HERE/.state"
KEYFILE="$HERE/${STACK}-key.pem"
AWS="aws --profile $AWS_PROFILE --region $REGION"
recall() { [ -f "$STATE/$1" ] && cat "$STATE/$1" || true; }

IID=$(recall instance); ALLOC=$(recall eip_alloc); EIP=$(recall eip_ip); SG=$(recall sg)

echo "About to destroy:"
echo "  instance      ${IID:-none}"
echo "  elastic ip    ${EIP:-none}"
echo "  security grp  ${SG:-none}"
echo "  key pair      $STACK"
read -rp "Type 'destroy' to confirm: " a
[ "$a" = "destroy" ] || { echo "aborted"; exit 1; }

if [ -n "$EIP" ] && [ -f "$KEYFILE" ]; then
  echo "→ rescuing demo state to deploy/data-backup.tgz"
  ssh -i "$KEYFILE" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
    "ubuntu@$EIP" 'cd ~/idatasight && tar czf - data' > "$HERE/data-backup.tgz" 2>/dev/null \
    && echo "  ✓ saved" || echo "  ! could not reach instance, skipping"
fi

[ -n "$IID" ] && { $AWS ec2 terminate-instances --instance-ids "$IID" >/dev/null
                   echo "→ terminating $IID (waiting)"
                   $AWS ec2 wait instance-terminated --instance-ids "$IID"; echo "  ✓"; }
# Elastic IPs bill whether attached or not — releasing is the step people forget.
[ -n "$ALLOC" ] && { $AWS ec2 release-address --allocation-id "$ALLOC" >/dev/null 2>&1 \
                     && echo "  ✓ released $EIP" || true; }
[ -n "$SG" ] && { $AWS ec2 delete-security-group --group-id "$SG" >/dev/null 2>&1 \
                  && echo "  ✓ deleted $SG" || true; }
$AWS ec2 delete-key-pair --key-name "$STACK" >/dev/null 2>&1 && echo "  ✓ deleted key pair" || true

rm -rf "$STATE"; rm -f "$KEYFILE"
echo
echo "Done — billing stopped. Remember to delete the DNS A record for $DOMAIN."
