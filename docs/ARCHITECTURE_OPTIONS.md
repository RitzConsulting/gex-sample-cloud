# Architecture Options — Cloud Migration Decision Reference

> Internal handover reference for the person taking over the migration. It
> explains the target-architecture decisions the exercises in this repo build
> toward. (If this repo is ever made public, keep *this* file private.)

## The one hard constraint

**IB Gateway cannot run serverless** — it's a GUI Java app needing a virtual
display (Xvfb), auto-login (IBC), and a weekly re-auth. So **wherever IBKR lives,
it needs a VM.** Everything else — Tastytrade/Tradier (REST), the dashboards, the
feeders, the trading engine — is flexible about where it runs.

## Path A vs Path B

| | **Path A — hardened VM(s)** (lift-and-shift) | **Path B — cloud-native split** |
|---|---|---|
| Effort | ~1.5–4 weeks | ~3–5 months |
| Code change | Near-zero | Significant (decouple the monolith) |
| Resilience | Single box(es) | Managed, isolated, autoscaled |
| DB | SQLite on persistent disk | Cloud SQL (HA, backups) |
| Do this | **First** (get off the local PC) | Later, iteratively |

**Do Path A first.** Path B still needs a VM for IB Gateway, so A is the
foundation B builds on.

## The IBKR decision (the crux)

IB Gateway is the flaky, VM-bound piece. Three options:

### 1. Drop IBKR — Tastytrade + Tradier only  ✅ simplest
No gateway at all. Options are already broker-agnostic → route to Tasty/Tradier.
Futures move to **Tastytrade** (REST, supports futures) or defer. Path A becomes
"run Python REST services on a hardened VM." Cost: lose the IBKR venue.

### 2. Keep IBKR local
- **Case 1 — fully local & self-contained** (recommended if IBKR is secondary):
  the local box owns the entire IBKR path; the cloud runs only Tasty/Tradier. **No
  cloud↔local wiring, nothing exposed.**
- **Case 2A — pull/queue:** cloud enqueues IBKR orders; the **local bridge polls
  the cloud** (outbound HTTPS), executes on the local IB Gateway, posts fills
  back. Socket stays `localhost`.
- **Case 2B — private tunnel** (Tailscale / reverse SSH): cloud reaches the local
  IB Gateway over an encrypted private link.
- **Catch:** in 2A/2B the cloud's IBKR trading now **depends on your home PC +
  internet** during market hours.

### 3. Keep IBKR in the cloud — on its **own small VM**  (best reliability)
IB Gateway + the futures bridge on a **dedicated VM**; the engine reaches it over
a **private VPC internal IP**, firewalled to the engine only, **no public
exposure of `:7496`**, ideally **no external IP** (egress via Cloud NAT). Cost:
2 VMs + solving headless IB Gateway.

**Same VM vs. separate VM (if option 3):** use a **separate** VM — isolate the
flaky gateway so its re-auth/crash/restart can't take down the Tasty/Tradier
strategies. Same-VM only for the absolute fastest Path A.

### Decision tree
- Want simplest / fastest → **Option 1** (drop IBKR).
- IBKR is secondary, home uptime OK → **Option 2 (Case 1)** (keep it local).
- IBKR must be as reliable as the cloud → **Option 3** (own VM, private-IP).

## Golden rules (security & ops)

- **Never expose IB Gateway `:7496` to the public internet.** Private VPC IP +
  firewall to engine-only, or the pull-queue. No `0.0.0.0/0` allow rule.
- **Partition by broker account** — no account is traded by two instances (real-
  money safety).
- **One "dashboard owner"** syncs to `intellitrade.live` — two sync workers would
  collide on `trade_ideas`/`trade_history` (independent auto-increment ids
  overwrite each other). The other instance's cloud sync is off, or namespaced.
- **IAP SSH**, no public app ports, per-service **least-privilege service
  accounts**, secrets in **Secret Manager**.
- **State is durable** — persistent disk (snapshots → GCS) or Cloud SQL. Never
  rely on ephemeral storage for source-of-truth data.

## Hybrid run — account map (fill this in)

The safety contract when running local + cloud in parallel:

| Broker account | Broker | Env (live/paper) | Owned by | Cloud-sync? |
|---|---|---|---|---|
| _e.g. Ritz TRD_ | Tradier | live | **cloud** | yes (owner) |
| _e.g. Ritz TT_ | Tastytrade | live | **cloud** | — |
| _e.g. Ritz IBKR_ | IBKR | live | **local** | — |

**Validation:** bring the cloud up in **paper/sandbox** for its accounts, run it
alongside live-local for ~1–2 weeks, compare trade ideas/fills for parity, then
flip the cloud accounts to live. Never double-trade the same account.

## How the repo exercises map to these decisions

| Exercise | Proves readiness for |
|---|---|
| **Cloud (Round 1 + `ROUND2.md`)** | Serverless Cloud Run, secrets, IAM → then persistence, auto-deploy, WAF, observability |
| **`vm-exercise/` Stage 1** | Single hardened VM: stateful service, persistent disk, **supervising the flaky IB-Gateway-analog**, alerting |
| **`vm-exercise/` Stage 2** | **Two VMs, private-only networking** — the **Option 3** (IBKR-on-its-own-VM) pattern |

Passing all three covers the full decision space above.
