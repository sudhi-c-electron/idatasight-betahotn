# iDataSight — Deployment Record

**Date:** 2026-08-07 · **Context:** hackathon, ~30 minute target
**Outcome:** deployed and verified live, then torn down. All billing stopped.

---

## 1. Outcome

| | |
|---|---|
| **Final URL** | `https://54.71.45.186.sslip.io` (live, verified, since destroyed) |
| **Intended URL** | `idatasight.consciouselectron.com` — **never achieved**, see §6.6 |
| **AWS account** | `789748176365` / IAM user `celectron_admin` |
| **Region** | `us-west-2` (Oregon) |
| **Instance** | `i-091b8bb7dbb6792a6` — t3.medium, Ubuntu 24.04 (`ami-0ac74609c6396bed3`) |
| **Elastic IP** | `54.71.45.186` (`eipalloc-0737d0dddd631a8e5`) |
| **Security group** | `sg-038699ed9669e725d` |
| **TLS** | Let's Encrypt, issued 2026-08-07 21:29:36 UTC |
| **Data source** | `IDATASIGHT_SOURCE=csv` (deliberate — see §6.3) |
| **Total cost** | ≈ $0.30 |
| **Teardown** | Complete. Instances, EIPs, volumes, snapshots all verified zero. |

---

## 2. Architecture as deployed

```
Browser
   │  https / wss
   ▼
Caddy :443  ── automatic Let's Encrypt cert, websocket-aware
   │
   ├─ /_event*, /_upload*, /ping, /_health, /_all_routes, /auth-codespace
   │     └──► reverse_proxy 127.0.0.1:8000
   │             reflex run --env prod --backend-only   (granian ASGI, systemd)
   │
   └─ everything else
         └──► file_server  /var/www/idatasight
                 static SPA from  reflex export --no-ssr
                 try_files {path} {path}/index.html {path}.html /index.html
```

**Key decision — Caddy serves the frontend as static files; no Node process runs
in production.** `reflex export --frontend-only --no-ssr` emits a pure SPA. The
backend runs `--backend-only`. Benefits: instant restarts, ~200 MB less RAM, one
less moving part. Cost: a UI change requires an explicit rebuild step.

**Ports:** only 22 (from deployer's IP), 80, 443 open. 3000/8000 never exposed —
Caddy reaches the backend over loopback.

---

## 3. Prerequisites and credentials

| Item | Where it came from | Notes |
|---|---|---|
| AWS IAM access key | IAM → Users → Security credentials | 20 chars, starts `AKIA`. See §6.5. |
| AWS region | chosen | `us-west-2` |
| Domain + DNS access | GoDaddy | `consciouselectron.com`, NS `ns69/ns70.domaincontrol.com` |
| EC2 key pair | created by `deploy.sh` | written to `deploy/idatasight-key.pem`, chmod 400 |
| Snowflake credentials | **not used** | CSV path chosen; see §6.3 |

Credentials were configured by the user directly via `aws configure --profile
idatasight` so secrets never entered the assistant transcript. The assistant only
ran `aws sts get-caller-identity` to verify.

---

## 4. The scripts

All live in `deploy/`. Idempotent and resumable — each completed step records
itself under `deploy/.state`, so a failure costs only the failed step.

| Script | Purpose |
|---|---|
| `config.env` | Single config file: domain, region, instance type, runtime env vars |
| `user-data.sh` | Runs as root on first boot. Installs swap, python3.12-venv, rsync, Caddy, uv — in parallel with instance boot, so the deploy script never waits on apt |
| `deploy.sh` | Full provision → live site. 11 phases, see §5 |
| `redeploy.sh` | Push code changes. Excludes `data/`. `--frontend` also rebuilds the bundle |
| `enable-snowflake.sh` | Phase 2: RSA key-pair auth, flip `IDATASIGHT_SOURCE`, verify it *actually* connected |
| `teardown.sh` | Rescue `data/`, then destroy everything and stop billing |

### `deploy.sh` phases

0. Preflight — validate config, verify AWS auth
1. SSH key pair (create or reuse)
2. Security group — 22 from deployer IP, 80, 443
3. EC2 instance — Ubuntu 24.04 AMI resolved live from SSM Parameter Store
4. Elastic IP — allocate + associate
5. **DNS gate** — print the exact A record, poll until it resolves
6. Wait for SSH, then for the user-data bootstrap marker
7. `rsync` code (exclusions in §6.2)
8. `uv venv` → install reflex → `reflex export` → publish to `/var/www` → **verify baked origin**
9. Caddy config + reload
10. systemd unit + enable
11. Verify `/ping` returns 200

---

## 5. What actually happened, in order

1. **Inspected the repo** rather than assuming. Found Reflex 0.9.8, Python 3.12,
   uv 0.8.16, bun 1.3.11, no git repo, `.web` at 217 MB, `data/` at 1 MB.
2. **Read `warehouse.py` and `hooks.py`** — discovered the Snowflake path uses
   browser OAuth (§6.3) and that `dispatch()` already offloads blocking work via
   `asyncio.to_thread`, so no async fix was needed.
3. **Wrote a 3-path decision doc** (EC2+Caddy / Cloudflare Tunnel / Reflex Cloud)
   and recommended EC2 because local disk had to persist.
4. **Wrote the automation** — five scripts, all syntax-checked.
5. **Tested the frontend export locally before deploying.** This caught the
   `REFLEX_API_URL` bug (§6.1) that would otherwise have shipped a dead app.
6. **Corrected the scripts and the runbook** for the three build-related findings.
7. **User configured credentials.** First attempt failed — account ID pasted into
   the access-key field (§6.5). Fixed on second attempt.
8. **First deploy run** — provisioned key pair, SG, instance, EIP. Reached the DNS
   gate. Printed the A record. Timed out after 10 minutes.
9. **GoDaddy rejected the record** with *"Invalid data provided for record data."*
   Diagnosed extensively; never resolved (§6.6).
10. **Pivoted to sslip.io** — wildcard DNS requiring zero configuration.
11. **Second deploy run** — failed at rsync: macOS ships rsync 2.6.9 (§6.7).
12. **Third deploy run** — completed. Live, with a real Let's Encrypt certificate.
13. **Verified independently** — not trusting the script's own check (§7).
14. **Teardown** — all resources destroyed, all billing stopped, verified.

---

## 6. Problems encountered

### 6.1 `REFLEX_API_URL`, not `API_URL` — **the most dangerous one**

**Severity:** would have silently shipped a non-functional demo.

Reflex's own self-hosting documentation says to set `API_URL`. On **Reflex 0.9.8
that is silently ignored.** The env-var prefix on 0.9.x is `REFLEX_`.

The value is compiled at build time into
`.web/build/client/assets/reflex-env-*.js` as the websocket origin. With the
wrong variable it stays:

```js
EVENT: `ws://localhost:8000/_event`
```

The deployed page then renders perfectly and responds to nothing — no error in
the UI, no error in the logs. A judge would see a beautiful frozen app.

**Proof (run against the project venv):**

```
API_URL=https://probe.test         → api_url = http://localhost:8000   (ignored)
REFLEX_API_URL=https://probe.test  → api_url = https://probe.test      (works)
```

**Fix:** export both `REFLEX_API_URL` and `REFLEX_DEPLOY_URL` before building.
`https://` is auto-upgraded to `wss://` for the websocket.

**Guard added:** `deploy.sh` and `redeploy.sh --frontend` both grep the built
bundle for `wss://$DOMAIN/_event` and abort on mismatch. Never trust the build.

### 6.2 Build output moved in Reflex 0.9

Reflex 0.9 uses React Router + Vite. Output is **`.web/build/client`**, not the
`.web/_static` that older docs describe.

It is also a **true SPA** — only `index.html` and `404.html`, no per-route HTML.
Without an SPA fallback, a deep link to `/analysis` would 404. Hence:

```
try_files {path} {path}/index.html {path}.html /index.html
```

**rsync exclusions and why each earns its place:**

| Excluded | Reason |
|---|---|
| `.web` | 217 MB of macOS-built artifacts; breaks on Linux; rebuilt server-side |
| `.venv` | 60 MB of macOS wheels |
| `.states` | pickled local session state, meaningless remotely |
| `reflex.lock` | bun lockfile resolved against macOS |
| `data` *(redeploy only)* | protects live demo state from being overwritten |

`data/` **is** included on first deploy — it carries the seed warehouse panels,
concept definitions, and `ledger.json`. The app is useless without it.

### 6.3 Snowflake cannot work headless — and fails *silently*

`warehouse.py:234`:

```python
conn = snowflake.connector.connect(connection_name=SF_CONNECTION)  # "MN74135"
```

This reads `~/.snowflake/connections.toml`, which is configured for **browser
OAuth**. A headless server has no browser, so the connect throws — and
`warehouse.py:250` catches **every** exception, prints one log line, and falls
back to the local CSV mirror:

```python
except Exception as e:
    print(f"[warehouse] snowflake read failed for {ds_id}: {e}; using CSV")
```

The UI is byte-identical either way. **You cannot tell from the screen whether
Snowflake is being used.** The log line is the only honest signal.

**Decision: ship on CSV deliberately.** `data/warehouse/` holds the same panels —
`warehouse.py` treats the sources as interchangeable by design — so the demo is
identical while removing an entire class of silent failure. Snowflake was
deferred to phase 2 via `enable-snowflake.sh` (RSA key-pair auth), which was
written and syntax-checked but **never run**.

**If enabling later, verify with the log, not the screen:**

```bash
journalctl -u idatasight --since '2 min ago' | grep -i 'snowflake read failed'
# silence = success
```

Also check Snowflake's network policy IP allowlist — it blocks with the same
invisible symptom.

### 6.4 EverOS — resolved differently than assumed

At deploy time, **nothing in the tree referenced EverOS.** The role it was
described as playing — a module needing local disk — was filled by `data/`,
specifically `data/store/ledger.json`, which `ledger_store.py` appends to on
every analysis run. That persistence requirement is what ruled out Reflex Cloud's
ephemeral filesystem and drove the EC2 choice.

The systemd unit therefore set a **placeholder**:

```ini
Environment="EVEROS_DATA_DIR=/home/ubuntu/idatasight/data/everos"
```

> **⚠ Known gap.** The project's actual convention is `EVEROS_ROOT`, with a
> storage root at `~/.everos`. The placeholder name above is **wrong** and the
> default root sits *outside* the app directory. Before any future deploy that
> includes EverOS, set `EVEROS_ROOT` to a persistent path on the instance
> (e.g. `/home/ubuntu/idatasight/data/everos`) and confirm the process user owns
> it — otherwise beliefs land in a location no backup covers.

### 6.5 AWS credential paste error

First `aws sts get-caller-identity` returned `InvalidClientTokenId`.

Diagnosis without printing secrets — inspect the *shape*:

```
access_key_id : len 12, prefix 7897     ← wrong
secret_key    : len 40                  ← correct
```

An AWS access key ID is **20 characters beginning `AKIA`** (or `ASIA` for
temporary credentials, which also require a session token). A **12-digit number
is an account ID** — and indeed the account turned out to be `789748176365`.
The account ID had been pasted into the Access Key ID field.

**Lesson:** validate credential *shape* before blaming permissions or policy.
Length and prefix identify the error instantly and leak nothing.

### 6.6 GoDaddy: "Invalid data provided for record data" — **UNRESOLVED**

This blocked the intended domain and was never solved.

**What was submitted** (confirmed correct by screenshot):

```
Type   A
Name   idatasight
Value  54.71.45.186
TTL    1 Hour
```

**Error:** `Invalid data provided for record data.`

**Ruled out by direct queries against GoDaddy's authoritative nameserver
(`ns69.domaincontrol.com`), bypassing all caching:**

| Hypothesis | Check | Result |
|---|---|---|
| Duplicate A record | `dig A idatasight… @ns69` | empty — name free |
| Conflicting CNAME | `dig CNAME idatasight… @ns69` | empty |
| Conflicting AAAA / TXT | `dig AAAA/TXT … @ns69` | empty |
| Doubled-domain typo | `dig A idatasight.consciouselectron.com.consciouselectron.com` | empty |
| Name field syntax | screenshot | `idatasight` — correct, bare label |
| Value malformed | screenshot | `54.71.45.186` — correct |
| Propagation delay | authoritative NS query | record never saved at all |
| TTL below minimum | — | user had "1 Hour", above the 600 s floor |

**Untested hypotheses, most plausible first:**

1. **Domain Connect / third-party zone management.** The apex resolves to
   `76.223.105.230` and `13.248.243.5` — AWS Global Accelerator IPs, typical of
   an **Amplify custom domain**. If that was configured through GoDaddy's Domain
   Connect integration, GoDaddy can reject manual record edits on the zone with
   exactly this generic error. **This is the leading candidate.**
2. **Invisible characters** from pasting into the Name or Value field.
3. **Stale CSRF / session state** — the form had been open a long time.
4. **Browser extension** interfering with the request.

**Suggested but never confirmed:** retype fields by hand, hard-reload the page,
try a private window or different browser.

**Resolution: none.** Worked around via §6.8 rather than solved.

**If revisiting:** check whether the zone is under Domain Connect management
(GoDaddy DNS page → look for a third-party "connected" banner), or use GoDaddy's
DNS API, which returns far more specific errors than the web form.

### 6.7 macOS ships rsync 2.6.9

```
rsync: unrecognized option `--info=stats1'
```

macOS ships `openrsync` / rsync 2.6.9-compatible, which predates `--info=`
(added in rsync 3.1, 2013). Removed the flag. **Lesson:** deploy scripts running
from macOS cannot assume GNU/modern userland — this applies to `rsync`, `sed -i`,
`date`, and `timeout` (which is also absent, and bit us once during local testing).

### 6.8 sslip.io — the unblock

With GoDaddy refusing, `sslip.io` provided wildcard DNS requiring **zero
configuration**: `<ip>.sslip.io` resolves to `<ip>`.

```
dig +short A 54.71.45.186.sslip.io  →  54.71.45.186
```

Because it is on the Public Suffix List, Let's Encrypt treats each IP-subdomain
as its own registered domain, so a **genuine certificate** is issued — no browser
warning, nothing to explain to judges.

Deployed against `54.71.45.186.sslip.io` and was live in ~6 minutes.

### 6.9 DNS gate timeout too short

The initial 10-minute poll was tuned for propagation delay, not for a human
fighting a web form. Raised to 25 minutes, and taught it to detect the
doubled-domain typo immediately rather than burning the whole window.

### 6.10 Teardown data rescue failed — **cause not diagnosed**

`teardown.sh` attempts to pull `data/` down before destroying anything. It
reported `could not reach instance, skipping` and left a **0-byte**
`deploy/data-backup.tgz`.

The rescue is correctly ordered *before* termination, so ordering was not the
cause. SSH failed for a reason that could not be investigated afterwards — the
instance was already gone.

**Impact: minimal.** Local `data/` was never touched (deploys only ever pushed it
upward; `redeploy.sh` excludes it). The only loss was demo-session state
generated *on the instance*.

**Fix for next time — teardown must refuse to destroy on an empty backup:**

```bash
[ -s "$HERE/data-backup.tgz" ] || { echo "backup empty — aborting"; exit 1; }
```

**Lesson:** a backup step that fails soft is not a backup. Verify the artifact is
non-empty before the irreversible action.

---

## 7. Verification performed

The deploy script's own health check was not trusted. Independent checks:

| Check | Command | Result |
|---|---|---|
| Page + TLS validity | `curl -w '%{http_code} %{ssl_verify_result}'` | 200, 0 (valid), 0.10 s |
| Certificate issuer | `openssl s_client … \| openssl x509 -issuer` | Let's Encrypt, valid to 2026-11-05 |
| Backend health | `curl /ping` | `"pong"` |
| **WebSocket upgrade** | `curl --http1.1 -H 'Upgrade: websocket' …/_event` | **101 Switching Protocols** |
| SPA deep links | `curl /analysis /beliefs /ledger` | 200, 200, 200 |
| Baked origin | `grep 'wss://…/_event' reflex-env-*.js` | correct |
| Services | `systemctl is-active idatasight caddy` | active, active |
| Memory headroom | `free -m` | 612 MB / 3834 MB |

**Two verification traps worth recording:**

- **`"Invalid transport"`** on a socket.io *polling* probe is **expected, not a
  fault** — Reflex is configured websocket-only, so it correctly rejects polling.
  The reply proves the backend is reachable through Caddy.
- **HTTP/2 returns 400 for a websocket upgrade.** `Connection: Upgrade` is
  invalid in HTTP/2. Must force `--http1.1` or the test is meaningless. The first
  attempt looked like a failure and was purely a test artifact.

---

## 8. Lessons learned

1. **Test the risky build step locally before provisioning anything.** Running
   `reflex export` on the laptop cost 3 minutes and caught the `REFLEX_API_URL`
   bug. Discovering it on the server, mid-hackathon, would have cost far more —
   and it presents as a *working-looking* app, the hardest failure to diagnose.

2. **Verify, don't trust — especially anything compiled at build time.** Every
   build-time-baked value deserves an assertion. `grep`ping the bundle is cheap
   insurance against the worst failure mode.

3. **Silent fallbacks are worse than crashes.** Two independent instances here:
   Snowflake falling back to CSV, and the wrong env var falling back to
   localhost. Both produce a healthy-looking system. Where a fallback exists,
   find the signal that distinguishes the paths and check *that*.

4. **Library docs go stale; the installed version is the truth.** The Reflex blog
   said `API_URL`; the installed 0.9.8 required `REFLEX_API_URL`. Two minutes of
   introspection beat the documentation.

5. **Diagnose credentials by shape, not by retrying.** Length and prefix
   identified the account-ID-in-key-field error immediately, without printing
   or transmitting a secret.

6. **Query authoritative nameservers when debugging DNS.** `dig @ns69.domain
   control.com` separated "not saved" from "not propagated" instantly — which
   redirected the whole GoDaddy investigation.

7. **Have an escape hatch that removes the blocking dependency entirely.**
   sslip.io eliminated DNS from the critical path. Under time pressure, an
   unblock that sidesteps the problem beats continuing to fight it. The real
   domain was always a one-line config change away.

8. **Make deploy scripts idempotent and resumable from the start.** `deploy.sh`
   ran four times. Because completed steps were recorded in `deploy/.state`,
   three retries cost seconds instead of full re-provisions.

9. **A backup that fails soft is not a backup.** §6.10.

10. **Don't assume GNU userland on macOS.** `rsync --info`, `timeout`, `sed -i`
    all differ or are absent.

11. **Ask which failure actually matters.** Rather than making the demo
    "correct" by wiring up live Snowflake, the right call was CSV — identical
    output, one less silent failure mode, six minutes saved for rehearsal.

---

## 9. Costs

| Line item | Rate | Actual (~1 hr) | If left a month |
|---|---|---|---|
| t3.medium | $0.0416/hr | $0.04 | $30.37 |
| 20 GB gp3 EBS | $0.08/GB-mo | $0.002 | $1.60 |
| Public IPv4 | $0.005/hr | $0.005 | $3.65 |
| Data transfer out | first 100 GB free | $0.00 | $0.00 |
| **Total** | | **≈ $0.30** | **$35.62** |

**The trap:** stopping an instance does *not* stop the bill. EBS and Elastic IPs
bill whether attached or not. Terminate **and** release.

---

## 10. Teardown, and how it was verified

```bash
./deploy/teardown.sh   # prompts for the literal word "destroy"
```

Post-teardown audit — every billable resource class in the region:

```bash
aws ec2 describe-instances  --query 'Reservations[].Instances[?State.Name!=`terminated`]'
aws ec2 describe-addresses                    # Elastic IPs
aws ec2 describe-volumes                      # orphaned EBS
aws ec2 describe-snapshots --owner-ids self
```

All four returned empty. Key pair and security group deleted.

**Do not stop at "the instance is terminated."** Orphaned EBS volumes and
released-but-still-allocated Elastic IPs are the classic silent charges.

---

## 11. Redeploying from scratch

Everything in `deploy/` is intact and reusable.

```bash
# 1. credentials (your own terminal — keeps secrets out of any transcript)
aws configure --profile idatasight

# 2. set the domain in deploy/config.env
#    both options are present; sslip.io needs the IP, which is only known
#    after provisioning — so start with the real domain, or deploy once,
#    read the IP, then switch.

# 3.
./deploy/deploy.sh
```

A fresh run creates a **new instance and a new Elastic IP**, so any sslip.io URL
will differ. Nothing needs cleaning up first.

**Iteration loop:**

```bash
./deploy/redeploy.sh              # ~40 s — event-handler bodies, backend/*.py
./deploy/redeploy.sh --frontend   # ~4 min — components, pages, theme,
                                  #          or any added/renamed State var
```

When unsure, use `--frontend`. A skipped rebuild serves a stale UI, which looks
exactly like the fix silently failing.

---

## 12. Outstanding items

| # | Item | Priority |
|---|---|---|
| 1 | **GoDaddy record still fails** — check for Domain Connect management on the zone, or use the GoDaddy DNS API for a specific error (§6.6) | High, if the real domain is required |
| 2 | **`EVEROS_ROOT` not wired** — systemd used a wrong placeholder name; default root `~/.everos` is outside the app dir and outside any backup (§6.4) | High, before any EverOS deploy |
| 3 | **`teardown.sh` must abort on empty backup** (§6.10) | Medium |
| 4 | **Snowflake never enabled** — `enable-snowflake.sh` written and syntax-checked, never executed | Medium |
| 5 | **Gitignore the SSH key** — `deploy/*.pem` and `deploy/.state/` must not reach `git@github.com:sudhi-c-electron/idatasight-betahotn.git` | **Critical before first push** |
| 6 | `deploy/data-backup.tgz` is a 0-byte artifact; delete it | Low |

---

## 13. Security notes

- Secrets never entered the assistant transcript. Credentials were configured by
  the user via `aws configure`; the assistant only ran `sts get-caller-identity`.
- `deploy/idatasight-key.pem` was chmod 400 and is deleted by `teardown.sh`.
- **Item 5 above is the live risk.** A `.pem` committed to a repo is a published
  private key. Add before the first push:

```gitignore
deploy/*.pem
deploy/.state/
deploy/data-backup.tgz
```

- SSH was restricted to the deployer's IP; 3000 and 8000 were never exposed.
- The IAM user `celectron_admin` holds broad permissions. For a longer-lived
  setup, a scoped deploy role would be preferable to admin credentials on a laptop.
